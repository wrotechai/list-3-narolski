; Task 2 — Vacuum robot (reference solution).
; The robot moves between rooms and cleans the room it is in.

(define (domain vacuum-robot)
  (:requirements :strips :typing)
  (:types robot room)

  (:predicates
    (at ?r - robot ?p - room)   ; the robot is in room ?p
    (dirty ?p - room)           ; room ?p is dirty
    (clean ?p - room)           ; room ?p is clean
  )

  (:action move
    :parameters (?r - robot ?from - room ?to - room)
    :precondition (at ?r ?from)
    :effect (and (not (at ?r ?from)) (at ?r ?to))
  )

  (:action clean
    :parameters (?r - robot ?p - room)
    :precondition (and (at ?r ?p) (dirty ?p))
    :effect (and (clean ?p) (not (dirty ?p)))
  )
)
