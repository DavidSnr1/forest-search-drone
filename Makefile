WORLD ?= baylands
MODEL ?= gz_x500_gimbal

.PHONY: sim stop

sim:
	./scripts/sim.sh start $(WORLD) $(MODEL)

stop:
	./scripts/sim.sh stop
