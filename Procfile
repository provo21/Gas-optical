web: uvicorn server:app --host 0.0.0.0 --port $PORT
promoter: python promoter.py
agent1: python agents/bazaar_crawler.py
agent2: python agents/directory_submitter.py
agent3: python agents/manifest_broadcaster.py
agent4: python agents/competitor_monitor.py
agent5: python agents/price_optimizer.py
agent6: python agents/health_reporter.py
