-- labs/w6d1_commit_refusal.sql -- Week 6 Din 1. Disposable database relay_w6d1 ONLY.
--
-- Two kinds of trigger, and the difference between them is the whole experiment:
--   w6d1_refuse_*  DEFERRABLE INITIALLY DEFERRED -> runs at COMMIT and makes that COMMIT fail.
--   w6d1_audit_*   ordinary AFTER UPDATE        -> its INSERT belongs to the same transaction,
--                  so it disappears whenever that transaction's COMMIT fails.
-- w6d1_audit therefore holds COMMITTED transitions only, counted by the database itself.

DO $$ BEGIN
  IF current_database() <> 'relay_w6d1' THEN
    RAISE EXCEPTION 'refusing to run in database %', current_database();
  END IF;
END $$;

CREATE TABLE w6d1_audit (
  kind   text        NOT NULL,
  row_id bigint      NOT NULL,
  at     timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE SEQUENCE w6d1_hb_seq;

CREATE FUNCTION w6d1_audit_row() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  INSERT INTO w6d1_audit (kind, row_id) VALUES (TG_ARGV[0], NEW.id);
  RETURN NULL;
END $$;

CREATE FUNCTION w6d1_refuse_commit() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  -- heartbeat arm: refuse only the FIRST heartbeat commit, allow the ones after it
  IF TG_ARGV[0] = 'heartbeat' AND nextval('w6d1_hb_seq') > 1 THEN
    RETURN NULL;
  END IF;
  RAISE EXCEPTION 'w6d1: % commit refused for id=%', TG_ARGV[0], NEW.id;
END $$;

-- audit: every committed transition of each kind, on every row
CREATE TRIGGER w6d1_audit_claim AFTER UPDATE ON jobs FOR EACH ROW
  WHEN (OLD.status = 'pending' AND NEW.status = 'running')
  EXECUTE FUNCTION w6d1_audit_row('claim');
CREATE TRIGGER w6d1_audit_heartbeat AFTER UPDATE ON jobs FOR EACH ROW
  WHEN (OLD.status = 'running' AND NEW.status = 'running' AND NEW.claimed_at > OLD.claimed_at)
  EXECUTE FUNCTION w6d1_audit_row('heartbeat');
CREATE TRIGGER w6d1_audit_mark AFTER UPDATE ON jobs FOR EACH ROW
  WHEN (OLD.status = 'running' AND NEW.status <> 'running' AND NEW.claimed_at IS NOT NULL)
  EXECUTE FUNCTION w6d1_audit_row('mark');
CREATE TRIGGER w6d1_audit_reclaim AFTER UPDATE ON jobs FOR EACH ROW
  WHEN (OLD.status = 'running' AND NEW.status = 'pending' AND NEW.claimed_at IS NULL)
  EXECUTE FUNCTION w6d1_audit_row('reclaim');
CREATE TRIGGER w6d1_audit_dispatch AFTER UPDATE ON outbox FOR EACH ROW
  WHEN (OLD.dispatched_at IS NULL AND NEW.dispatched_at IS NOT NULL)
  EXECUTE FUNCTION w6d1_audit_row('dispatch');

-- refusal: one arm per lifecycle writer, selected by the row's payload
CREATE CONSTRAINT TRIGGER w6d1_refuse_claim AFTER UPDATE ON jobs
  DEFERRABLE INITIALLY DEFERRED FOR EACH ROW
  WHEN (OLD.status = 'pending' AND NEW.status = 'running' AND NEW.payload->>'fail_commit' = 'claim')
  EXECUTE FUNCTION w6d1_refuse_commit('claim');
CREATE CONSTRAINT TRIGGER w6d1_refuse_heartbeat AFTER UPDATE ON jobs
  DEFERRABLE INITIALLY DEFERRED FOR EACH ROW
  WHEN (OLD.status = 'running' AND NEW.status = 'running' AND NEW.claimed_at > OLD.claimed_at
        AND NEW.payload->>'fail_commit' = 'heartbeat')
  EXECUTE FUNCTION w6d1_refuse_commit('heartbeat');
CREATE CONSTRAINT TRIGGER w6d1_refuse_mark AFTER UPDATE ON jobs
  DEFERRABLE INITIALLY DEFERRED FOR EACH ROW
  WHEN (OLD.status = 'running' AND NEW.status <> 'running' AND NEW.claimed_at IS NOT NULL
        AND NEW.payload->>'fail_commit' = 'mark')
  EXECUTE FUNCTION w6d1_refuse_commit('mark');
CREATE CONSTRAINT TRIGGER w6d1_refuse_reclaim AFTER UPDATE ON jobs
  DEFERRABLE INITIALLY DEFERRED FOR EACH ROW
  WHEN (OLD.status = 'running' AND NEW.status = 'pending' AND NEW.claimed_at IS NULL
        AND NEW.payload->>'fail_commit' = 'reclaim')
  EXECUTE FUNCTION w6d1_refuse_commit('reclaim');
CREATE CONSTRAINT TRIGGER w6d1_refuse_dispatch AFTER UPDATE ON outbox
  DEFERRABLE INITIALLY DEFERRED FOR EACH ROW
  WHEN (OLD.dispatched_at IS NULL AND NEW.dispatched_at IS NOT NULL
        AND NEW.payload->>'fail_commit' = 'dispatch')
  EXECUTE FUNCTION w6d1_refuse_commit('dispatch');

-- seeds: ids 1..3 share one created_at, so the claim order is by id
INSERT INTO jobs (type, payload) VALUES
  ('sleep', '{"seconds": 0.5, "fail_commit": "mark"}'),
  ('sleep', '{"seconds": 22,  "fail_commit": "heartbeat"}'),
  ('sleep', '{"seconds": 0.5, "fail_commit": "claim"}');
INSERT INTO jobs (type, payload, status, attempts, claim_generation, claimed_at)
  VALUES ('sleep', '{"fail_commit": "reclaim"}', 'running', 1, 1, now() - interval '60 seconds');
INSERT INTO outbox (job_id, effect_key, payload)
  VALUES (99, 'job:99', '{"fail_commit": "dispatch"}');

SELECT 'seeded_jobs=' || count(*) FROM jobs;
SELECT 'triggers=' || count(*) FROM pg_trigger WHERE tgname LIKE 'w6d1\_%';
