; Task 1 — Package transport / logistics (reference solution).
;
; Packages are loaded onto vehicles, vehicles travel along the transport
; topology, and packages are unloaded at their destination. Two transport
; modes are modelled: trucks travel along ROADS (within a city) and planes
; travel along AIR links (between airports).

(define (domain package-transport)
  (:requirements :strips :typing)
  (:types
    package location vehicle - object
    truck plane - vehicle
  )

  (:predicates
    (at-pkg ?p - package ?l - location)   ; package is at a location
    (at-veh ?v - vehicle ?l - location)   ; vehicle is at a location
    (in ?p - package ?v - vehicle)        ; package is loaded on a vehicle
    (road ?from - location ?to - location); road link (trucks)
    (air ?from - location ?to - location) ; air link (planes)
  )

  (:action load
    :parameters (?p - package ?v - vehicle ?l - location)
    :precondition (and (at-pkg ?p ?l) (at-veh ?v ?l))
    :effect (and (not (at-pkg ?p ?l)) (in ?p ?v))
  )

  (:action unload
    :parameters (?p - package ?v - vehicle ?l - location)
    :precondition (and (in ?p ?v) (at-veh ?v ?l))
    :effect (and (at-pkg ?p ?l) (not (in ?p ?v)))
  )

  (:action drive
    :parameters (?t - truck ?from - location ?to - location)
    :precondition (and (at-veh ?t ?from) (road ?from ?to))
    :effect (and (not (at-veh ?t ?from)) (at-veh ?t ?to))
  )

  (:action fly
    :parameters (?pl - plane ?from - location ?to - location)
    :precondition (and (at-veh ?pl ?from) (air ?from ?to))
    :effect (and (not (at-veh ?pl ?from)) (at-veh ?pl ?to))
  )
)
