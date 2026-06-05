import sys
sys.path.insert(0, 'E:\\openclaw-data\\.openclaw\\plugins\\brain-memory')
import os
os.environ['OLLAMA_MODELS'] = 'D:\\ollama_models'

from memory_backend import BrainMemoryBackend

brain = BrainMemoryBackend()
count = brain.backfill_chat_history('E:\\openclaw-data\\.openclaw\\chat_history.db')
print(f'总计回填: {count} 条')
stats = brain.get_stats()
total = stats.get('total_memories', 0)
print(f'当前记忆总数: {total}')
