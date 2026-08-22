# POSTMORTEMS.md

Weekly incident postmortems and external system failure analyses.

---

## Incident 01 — Buttondown: Database Connection Exhaustion (Week 0, Day 3)

**Source:** [Buttondown incident 0024](https://buttondown.com/blog/incident-0024)
*Summary paraphrased; see source for the full writeup.*

**What broke:** New requests could not acquire a database connection, so they failed or hung. From the outside the application looked like it had a slow or failing database.

**Root cause:** The configured connection ceiling was reached. There were no connections left to hand out, so incoming work had nowhere to go — the database itself was not the failing component.

**What I learned:** Connection exhaustion impersonates database slowness. The symptom (requests taking long or failing) points at the database, but the actual constraint sits in the application's connection layer. Debugging in the wrong layer is the default failure mode here.

**Evidence from my own experiments the same day:** I reproduced this shape locally with `pool_size=2` and 10 concurrent 1-second queries.
- Total time was **5.25s** for work that was only 1 second deep, because requests queued for connections. REQ 10 reported **5.20s latency for a 1s query** — roughly **4.2s of pure waiting**.
- With `pool_timeout=1` the failures surfaced as `QueuePool limit of size 2 overflow 0 reached, connection timed out` — thrown by **SQLAlchemy, not Postgres**. Those requests never reached the database, which means Postgres-side monitoring would have shown a perfectly healthy database while 8 of 10 requests failed.
- Raising `pool_size` to 10 dropped total time to **1.66s**, confirming the pool was the bottleneck.

**What this means for Relay:**
1. I have never consciously chosen a `pool_size` — it has always been a default I ignored. That is an unowned failure mode. → future `DECISIONS.md` entry.
2. `workers × pool_size` must stay under Postgres `max_connections` (default 100), otherwise the failure moves to a different layer with a different error (`FATAL: sorry, too many clients already`) and a different fix.
3. Latency alone cannot detect this. Relay's observability needs **error rate and pool wait time** alongside latency, because a fail-fast config makes latency graphs look *better* while dropping work.
4. Enqueue needs a deliberate saturation policy — wait, or reject with 503 and let the caller retry. Silent waiting is the default, and defaults are how incidents like this happen.

**Still to verify:** I have not yet confirmed with `pg_stat_activity` that my configured pool size matches the actual connection count on the server side, and I have not read the full writeup closely enough to capture their detection and remediation timeline. Both are follow-ups.

---

## INCIDENT 02 - GITHUB : Cross-layer assumption mismatch causing an emergent distributed systems failure.

summary : 

Background :

This section is first setting up the scene of the incident. Before explaining what actually went wrong, GitHub explains how its infrastructure normally works, because without that, the later failure would not make sense.

1. GitHub is a distributed system

GitHub does not run everything on one server or in one location. Its user-facing services run across its own data centers, network hubs, POPs, and other infrastructure.

Users
  ↓
GitHub Edge / Network
  ↓
Network Hubs / POPs
  ↓
Regional Data Centers
  ↓
Applications + Databases + Storage + Workers

These different physical locations need to communicate with each other. Even though GitHub has physical and logical redundancy, communication between two healthy locations can still temporarily break. This is an important distributed-systems concept: a machine being unreachable does not necessarily mean the machine itself is dead; the network path may be the problem.

2. The initial physical problem was very short

During routine maintenance, GitHub was replacing failing 100G optical networking equipment.

This accidentally caused the connection between:

US East Coast Network Hub
          X
Primary US East Coast Data Center

to disappear.

The connectivity was restored in only 43 seconds.

However, those 43 seconds triggered automated systems to react to what they observed as a failure. The physical network problem was fixed quickly, but the system state changes and decisions triggered during those 43 seconds continued causing problems.

That is why:

43-second connectivity loss
          ↓
Chain of automated reactions
          ↓
System state/topology changes
          ↓
Long-term service degradation
          ↓
24 hours 11 minutes

So the investigation is already pointing toward an important question:

What did GitHub's distributed systems do during those 43 seconds that made the consequences last for more than 24 hours?

3. GitHub's application data is heavily dependent on MySQL

GitHub uses multiple MySQL clusters to store metadata, meaning application data beyond raw Git objects.

This includes functionality such as:

Pull requests
Issues
Authentication
Background processing
Other GitHub application features

GitHub's data is divided across different MySQL clusters using functional sharding, meaning different parts/functions of the application store their data in different database clusters.

4. Each MySQL cluster has a primary and many replicas

The basic architecture is:

                 MySQL Cluster
                      │
                   Primary
                  /   |   \
                 ▼    ▼    ▼
               R1    R2    R3...

Applications generally:

Writes → Primary
Reads  → Replica servers

This allows GitHub to scale because the primary does not have to handle the huge majority of read traffic.

Each cluster can have up to dozens of read replicas.

5. Orchestrator manages the database topology

GitHub uses Orchestrator to manage MySQL cluster topology and automated failover.

For example:

Normal state:

Primary
  ├── Replica 1
  ├── Replica 2
  └── Replica 3

If the primary appears to fail, Orchestrator can automatically change the topology and promote another server.

Primary unreachable
        ↓
Orchestrator reacts
        ↓
Choose a suitable replica
        ↓
Promote it as new Primary

Orchestrator makes these distributed decisions using multiple variables and uses Raft consensus so the system can coordinate important decisions.

6. The critical risk introduced here

The most important warning in this background is:

Orchestrator can create a database topology that is technically valid, but that GitHub's applications may not know how to support.

In other words:

Orchestrator:
"I can create this topology."

Application:
"I was not designed to work with this topology."

Therefore, Orchestrator's possible configurations must match application-level expectations.

Possible states created by Orchestrator
                ↓
Must be supported by
                ↓
GitHub applications
Where we are in the investigation

We now know the basic environment in which the incident happened:

Distributed GitHub infrastructure
        ↓
Multiple network locations communicate
        ↓
GitHub applications depend on MySQL clusters
        ↓
Primary handles writes, replicas handle most reads
        ↓
Orchestrator manages database topology/failover
        ↓
A 43-second network partition occurs
        ↓
Automated systems may react and change topology
        ↓
The resulting state may not match what applications expect.


INCIDENT TIMELINES :

1. as of network partition, inside this infrastructure, there were multiple orchestrator nodes that were distributed across locations. orchestrator had an active leader associated with primary data center.

                 Orchestrator Cluster

                    Leader
                      │
                      │
            ┌─────────┼─────────┐
            ▼         ▼         ▼
         East DC     West      East Cloud

current leader was affected by connectivity problem, then cluster began a process of leadership deselection(other nodes observe : leader is not reachable).


Network partition
       ↓
Existing leader becomes unreachable
from other participating nodes
       ↓
Leadership deselection process begins
       ↓
Remaining nodes attempt to establish
a valid consensus state


This is important because the system was not waiting for a human to decide what to do. The distributed automation was already reacting.

- Quorum = enough participating nodes available to form and make valid decisions.

East Data Center
   │
   │ temporarily partitioned
   X
   │
──────────────────────────────

West Coast + East Cloud
        │
        ▼
      Quorum
        │
        ▼
Can make valid Orchestrator decisions


normal data base model : 

APLLICATION
   │
   ▼
Writes
   │
   ▼
East Coast Primary
   │
   └── replication toward other servers/sites


during failover : 

East connectivity problem
        ↓
Orchestrator quorum survives elsewhere
        ↓
Failover initiated
        ↓
West Coast database becomes primary
        ↓
Writes should now go West.


so now new situation is : writes -> west coast primary.

The important thing is that Orchestrator was actively changing the structure of multiple database clusters while the original network problem was happening.

Before:

East Primary
    │
    ├── East/other replicas
    └── replication relationships


After failover:

West Primary
    │
    ├── West Replica 1
    ├── West Replica 2
    └── new topology relationships

NETWORK COMES BACK - DATABASE STATE CHANGED :

- physical network problem is over after 43 seconds, but system does not simply revert to its old state, because as old conn breaks, orchestrator leadership changed, west coast primaries are established. so application tier sees new primaries.(instead returning to east primary, system transitioned to west primary).
- now application sends writes to them(US WEST COAST)

- DATA INCONSISTENCY PROBLEM :
before the network partition, some writes happened in east coast, for a brief periods, those writes were not successfully replicated to west coast.

East Coast Database:   West Coast Database

Write A ✓               Write A ✓  (A)
Write B ✓              Write B ✗
Write C ✓              Write C ✗

after failover, new writes were received on west coast.(eg : A, G, H, J).
- database clusters in both data centers now contained writes that were not present in the other data center.

WHY NOT MOVE PRIMARY BACK TO EAST COAST WHEN NETWORK IS BACK ?
- not safe, west had new writes, which would be lost if primary was moved back to east.


NOW, MONITORING STARTS REPORTING FAILURES :

Database system fault
       ↓
Monitoring detects it
       ↓
Alert

Application fault
       ↓
Monitoring detects it
       ↓
Alert

Other dependency fault
       ↓
Monitoring detects it
       ↓
Alert

- so engineers dont know the root cause yet : they ask : are these separate problems or are they symptoms of one underlying event?.

GitHub
 ├── Cluster A
 ├── Cluster B
 ├── Cluster C
 ├── Cluster D
 └── ...
- many of them moved into a state that engineers did not expect, so they query orchestrator API.

ORCHESTRATOR API : 

Database Topology :

West Primary
   ├── West Replica 1
   ├── West Replica 2
   └── West Replica 3

Only West Coast servers appear.

This is exactly an unexpected topology state.

The system is now effectively operating around the West Coast database cluster.

INCIDENT-RESPONSE ACTION :
- The worst thing you can do during a poorly understood incident is continue introducing unrelated changes.

For example:

Incident is happening
        +
New code deployment
        +
Configuration change
        +
Database migration

Now debugging becomes harder.

Which change caused which problem?

so git hub manually locks deployment tooling:

production state frozen -> no additional deployment changes can enter -> engineers can investigate more stable situation.

now GITHUB had options : west primary -> discard new writes -> return to east primary (old architecture) OR continue forward from west -> preserve the use data -> rebuild safety.

so they chose second option(rebuild). but architecture was NOT designed for this : 

instead of :
East Application
      │
      │ Local / nearby database call
      ▼
East Database

they now had :
East Application
      │
      │ Cross-country network trip
      ▼
West Coast Database
      │
      │ Response travels back
      ▼
East Application.

this creates cross country round trip.

LATENCY :
- a database call has : application -> db -> application, this is one round trip, but as application and sb are not nearby anymore, latency is higher. now application cant cope-up with the additional latency. 

RECOVERY PLAN :

Keep West Primary temporarily
        ↓
Restore/rebuild East Coast databases
        ↓
Synchronize East with the new data from West
        ↓
Wait until replication catches up
        ↓
Once both sides are consistent
        ↓
Safely move primary back to East
        ↓
Restore the original topology.

So they did not choose West because it was a good architecture. They chose it because, at that moment, switching back to East would risk losing valid user data. They accepted terrible latency temporarily so they could first make the data consistent, and only then safely return the primary to East.



what broke :
A 43-second network partition caused Orchestrator to fail over multiple MySQL primaries from the East Coast to the West Coast. The physical network recovered quickly, but the database topology and write paths had already changed, causing long latency, replication lag, inconsistent reads, and a large processing backlog.


root cause :
The core failure was an unsafe system boundary/assumption mismatch: Orchestrator was allowed to promote primaries across regions, but the application tier could not tolerate cross-country database latency. Network partition + Raft quorum made the failover technically valid, but the resulting topology was not operationally supported by the application.


what i learned :
A distributed system can recover from the original failure while remaining broken because automated recovery actions change system state. "The component is reachable again" does not mean "the system can safely return to its previous state"; data divergence and accumulated writes can make rollback unsafe.


evidence from my own experiments :
In Relay, my worker experiments showed that system state can be contaminated by processes outside the experiment boundary: stray workers kept running, claimed jobs, and affected later measurements. I also observed why claiming must be committed before execution—otherwise concurrent workers can create incorrect or duplicate state.



what this means for relay :
Relay must define exactly which states and topology/failure transitions the application supports, rather than assuming infrastructure recovery automatically preserves correctness. Job claiming, worker crashes, retries, stale locks, duplicate execution, and recovery must be designed as explicit state transitions, with data correctness taking priority over simply making the queue appear available.



still to verify :
I still need to deliberately test Relay's failure boundaries: worker dies after claim, dies during execution, dies after handler succeeds but before marking success, multiple workers race, database/network interruption, and recovery after restart. The important question is whether every infrastructure-valid recovery state is also application-safe.


Unka mental model :

Network partition
      ↓
Orchestrator safely detects failure
      ↓
Valid Raft quorum
      ↓
Valid database failover
      ↓
System continues working



reality/system boundary :

Network partition
      ↓
Orchestrator makes a technically valid failover
      ↓
Primary moves across the country
      ↓
Application latency assumptions are violated
      ↓
Both regions accumulate different writes
      ↓
Rollback is no longer safely possible
      ↓
Infrastructure recovered, but the SYSTEM remained broken

---

