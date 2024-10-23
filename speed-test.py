import time, threading
from hololinked.client import ObjectProxy


oscilloscope_sim = ObjectProxy('oscilloscope_sim')

number_of_runs = 1000
start_time = time.perf_counter() 
for i in range(number_of_runs):
    oscilloscope_sim.set_trigger(enabled=True, channel='A', threshold=0.5, adc=True, direction='rising', delay=0, auto_trigger=0)
elapsed_time = time.perf_counter() - start_time
print(f"total time set trigger with schema is {(elapsed_time/number_of_runs) * 1_000_000:.6f} microseconds per call")

start_time = time.perf_counter() 
for i in range(number_of_runs):
    oscilloscope_sim.set_trigger_no_schema(enabled=True, channel='A', threshold=0.5, adc=True, direction='rising', delay=0, auto_trigger=0)
elapsed_time = time.perf_counter() - start_time
print(f"total time is set trigger no schema {(elapsed_time/number_of_runs) * 1_000_000:.6f} microseconds per call")
# apparently its not so bad as we thought, I guess the original tests were done suboptimally 

event = threading.Event()
def wait_for_event(data):
    print(f"event arrived at {data}")
    event.set()
oscilloscope_sim.subscribe_event('data-ready-event', callbacks=[wait_for_event])
time.sleep(0.1) # allow PUB-SUB to connect
oscilloscope_sim.start(max_count=1)
event.wait()


for time_range in [1e-3, 1e-2, 1e-1]:
    oscilloscope_sim.time_range = time_range
    print("len channels - ", len(oscilloscope_sim.channel_A), len(oscilloscope_sim.channel_B), len(oscilloscope_sim.channel_C), len(oscilloscope_sim.channel_D))
    len_data = len(oscilloscope_sim.channel_A)
    oscilloscope_sim.start(max_count=1)
    start_time = time.perf_counter()
    for i in range(number_of_runs):
        # just access to trigger serialization
        oscilloscope_sim.channel_A
        oscilloscope_sim.channel_B
        oscilloscope_sim.channel_C
        oscilloscope_sim.channel_D
    elapsed_time = time.perf_counter() - start_time
    print(f"total time to load channels of {len_data} elements is {(elapsed_time/number_of_runs) * 1_000_000:.6f} microseconds per call")

oscilloscope_sim.unsubscribe_event('data-ready-event')