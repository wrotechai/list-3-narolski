; Task 1 — Package transport problem (reference solution).
;
; Topology:  City A: depotA --road-- airportA
;            City B: storeB --road-- airportB
;            Air link: airportA --air-- airportB
;
; pkg1: depotA  -> storeB   (needs truck + plane + truck: road, air, road)
; pkg2: depotA  -> airportA (same city: truck only, road)

(define (problem deliver-packages)
  (:domain package-transport)

  (:objects
    depotA airportA storeB airportB - location
    truckA truckB - truck
    plane1 - plane
    pkg1 pkg2 - package
  )

  (:init
    ; vehicles
    (at-veh truckA depotA)
    (at-veh truckB storeB)
    (at-veh plane1 airportA)

    ; packages
    (at-pkg pkg1 depotA)
    (at-pkg pkg2 depotA)

    ; road topology (bidirectional)
    (road depotA airportA) (road airportA depotA)
    (road storeB airportB) (road airportB storeB)

    ; air topology (bidirectional)
    (air airportA airportB) (air airportB airportA)
  )

  (:goal
    (and
      (at-pkg pkg1 storeB)
      (at-pkg pkg2 airportA)
    )
  )
)
