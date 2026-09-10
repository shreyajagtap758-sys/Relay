import os
import pytest


class RelayModel:

  def __init__(self, mutant: bool = False):
    self.status = "pending"
    self.attempts = 0
    self.dispatches = 0
    self.effects = []  # durable effects
    self.mutant = mutant  # If True, dedup disabled

  def claim(self, worker_id: str):
    assert self.status == "pending"
    self.status = "running"
    self.attempts += 1
    self.dispatches += 1

  def effect_write(self, key: str):
    assert self.status == "running"
    if self.mutant:
      self.effects.append(key)  # BUG: No dedup, append every time!
    else:
      if key not in self.effects:
        self.effects.append(key)  # ON CONFLICT DO NOTHING

  def crash(self):
    assert self.status == "running"
    # Worker dies without changing status

  def reclaim(self):
    assert self.status == "running"
    self.status = "pending"

  def mark_succeeded(self):
    assert self.status == "running"
    self.status = "succeeded"


# 4 Deterministic Unit Tests:
def test_zero_writes_has_zero_effects():
  m = RelayModel()
  m.claim("w1")
  m.crash()
  assert len(m.effects) == 0


def test_one_dispatch_one_effect():
  m = RelayModel()
  m.claim("w1")
  m.effect_write("job:1:email")
  m.mark_succeeded()
  assert len(m.effects) == 1
  assert m.dispatches == 1


def test_reclaim_two_dispatches_one_effect():
  m = RelayModel()
  m.claim("w1")
  m.effect_write("job:1:email")
  m.crash()
  m.reclaim()
  m.claim("w2")
  m.effect_write("job:1:email")  # Duplicate write
  m.mark_succeeded()
  assert m.dispatches >= 2  # Dispatches must be >= 2
  assert len(m.effects) == 1  # Dedup held it to 1!


def test_p27_extra_dispatch_preserves_safety():
  m = RelayModel()
  for _ in range(4):  # P-27 overdraft (4 dispatches)
    m.claim("w")
    m.effect_write("job:1:email")
    m.reclaim()
  assert m.dispatches >= 2
  assert len(m.effects) <= 1  # Safety predicate <= 1 holds!



import json
from hypothesis import given, settings
from hypothesis import strategies as st

# Strategies for actions
actions_strategy = st.lists(
    st.sampled_from(["claim", "write", "crash", "reclaim", "mark"]),
    min_size=1,
    max_size=30,
)


@settings(max_examples=200, deadline=None)
@given(actions=actions_strategy)
def test_all_action_sequences_preserve_effect_safety(actions):
  m = RelayModel(mutant=os.getenv("DIN5_MUTANT") == "no_dedup")
  key = "job:1:email"
  for act in actions:
    try:
      if act == "claim" and m.status == "pending":
        m.claim("w")
      elif act == "write" and m.status == "running":
        m.effect_write(key)
      elif act == "crash" and m.status == "running":
        m.crash()
      elif act == "reclaim" and m.status == "running":
        m.reclaim()
      elif act == "mark" and m.status == "running":
        m.mark_succeeded()
    except AssertionError:
      pass
  # Invariant: Side effect hamesha <= 1
  assert len(m.effects) <= 1


# Forced-Redispatch: At least 2 dispatches guaranteed
@settings(max_examples=100, deadline=None)
@given(tail=actions_strategy)
def test_redispatch_sequences_preserve_effect_safety(tail):
  m = RelayModel(mutant=os.getenv("DIN5_MUTANT") == "no_dedup")
  key = "job:1:email"
  # Guaranteed 2-dispatch skeleton:
  m.claim("w1")
  m.effect_write(key)
  m.reclaim()
  m.claim("w2")
  m.effect_write(key)

  # Followed by random tail actions:
  for act in tail:
    try:
      if act == "claim" and m.status == "pending":
        m.claim("w")
      elif act == "write" and m.status == "running":
        m.effect_write(key)
      elif act == "crash" and m.status == "running":
        m.crash()
      elif act == "reclaim" and m.status == "running":
        m.reclaim()
      elif act == "mark" and m.status == "running":
        m.mark_succeeded()
    except AssertionError:
      pass

  # Invariant check:
  if m.mutant and len(m.effects) > 1:
    # Print for shrinking observation
    print(
        f"shrunk_trace=redispatch; dispatches={m.dispatches};"
        f" effect_count={len(m.effects)}"
    )
  assert len(m.effects) <= 1