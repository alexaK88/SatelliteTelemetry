from simulator.telemetry_generator import TelemetrySimulator

sim = TelemetrySimulator()

packet = sim.generate_packet()
print(packet.model_dump())

faulty = sim.generate_packet(fault="LOW_BATTERY")
print(faulty.measurements.power)
