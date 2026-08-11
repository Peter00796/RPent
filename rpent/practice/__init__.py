"""The practice loop: ASPIRE's debugger, with the playbook as the program.

One cell, iterated until it cracks:

    round:
      ATTEMPT the task on each practice seed (normal brief, playbook armed)
        solved all -> EXAM on the scoring seed, one attempt, report honestly
        failed     -> MINE the failure (observe) and UPDATE the playbook
                      (task-scoped proposals through the same gate checks;
                      only mechanically-clean ones auto-admit)
      knowledge stalled (nothing admitted)? -> next round runs an EXPERIMENT
      episode instead, on the OPEN QUESTION the miner itself raised.

    stop: exam solved, or max rounds spent. Every episode, proposal and
    verdict lands in the same evidence trail as everything else.

The turn-loop analogue of ``rpent.cap``: there the artifact debugged
between episodes is a program; here it is the task playbook. Same seed
discipline (practice seeds learn, the scoring seed only examines), same
iron rule (evidence cites run records).
"""
