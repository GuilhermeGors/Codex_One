import requests
import json
import time

API_URL = "http://localhost:8000/api/v1/query/stream"

QUERY_PAYLOAD = {
    "query": "Who was the employee involved in the unauthorized database export in Incident INC-2024-001, and what are her contact details and SSN?"
}

def run_benchmark(num_runs=3):
    print(f"Starting Benchmark on {API_URL} ({num_runs} runs)")
    
    total_metrics = {
        "latency_embedding_ms": 0,
        "latency_retrieval_ms": 0,
        "latency_reranking_ms": 0,
        "latency_generation_ms": 0,
        "latency_total_ms": 0
    }
    
    success_runs = 0

    for i in range(num_runs):
        print(f"\n--- Run {i+1} ---")
        try:
            start_time = time.perf_counter()
            response = requests.post(API_URL, json=QUERY_PAYLOAD, stream=True)
            
            final_metrics = None
            for line in response.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8')
                    if decoded_line.startswith("data: "):
                        data = json.loads(decoded_line[6:])
                        print(f"   -> Stage: {data.get('stage')} | Status: {data.get('status')} | {data.get('detail', '')}")
                        if data.get("stage") == "error":
                            print(f"   -> ERROR: {data.get('detail', {}).get('message', 'Unknown Error')}")
                        if data.get("stage") == "complete":
                            final_metrics = data.get("detail", {}).get("metrics", {})
                            
            total_time = (time.perf_counter() - start_time) * 1000
            
            if final_metrics:
                print(f"Success in {total_time:.0f}ms")
                for key in total_metrics.keys():
                    total_metrics[key] += final_metrics.get(key, 0)
                success_runs += 1
            else:
                print("Failed to get final metrics from SSE stream")
                
        except Exception as e:
            print(f"Error: {e}")

    if success_runs > 0:
        print("\n--- BENCHMARK RESULTS (Averages) ---")
        print(f"Runs: {success_runs}")
        print(f"Embeddings (FastEmbed): {total_metrics['latency_embedding_ms']/success_runs:.0f} ms")
        print(f"Retrieval (ChromaDB):   {total_metrics['latency_retrieval_ms']/success_runs:.0f} ms")
        print(f"Reranking (FlashRank):  {total_metrics['latency_reranking_ms']/success_runs:.0f} ms")
        print(f"Generation (Ollama):    {total_metrics['latency_generation_ms']/success_runs:.0f} ms")
        print(f"Total Query Latency:    {total_metrics['latency_total_ms']/success_runs:.0f} ms")
    else:
        print("No successful runs to average.")

if __name__ == "__main__":
    run_benchmark(3)
