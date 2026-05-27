# Build and run counter TB with VCD trace (requires Verilator)
VERILATOR ?= verilator
BUILD_DIR ?= obj_dir
WAVE_DIR  ?= waves

.PHONY: all run clean waves

all: run

$(BUILD_DIR)/Vcounter: counter.sv sim_main.cpp
	$(VERILATOR) --cc --exe --build --trace -Wno-UNOPTFLAT \
		-Mdir $(BUILD_DIR) counter.sv sim_main.cpp

run: $(BUILD_DIR)/Vcounter
	@mkdir -p $(WAVE_DIR)
	./$(BUILD_DIR)/Vcounter
	@echo "Wrote $(WAVE_DIR)/test_counter_sim.vcd"

waves: run

clean:
	rm -rf $(BUILD_DIR) $(WAVE_DIR)
