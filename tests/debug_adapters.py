import sys
import os

# Add src paths to ensure imports work
sys.path.append(os.path.abspath("packages/gyra-core/src"))
sys.path.append(os.path.abspath("packages/gyra-serve/src"))
sys.path.append(os.path.abspath("packages/gyra-ext/src"))
sys.path.append(os.path.abspath("packages/gyra-app/src"))

try:
    # Trigger imports to ensure registration decorators run
    import gyra.rag.embedding
    from gyra.rag.embedding import embedding_factory
    from gyra.rag.embedding.embeddings import HuggingFaceEmbeddings
    from gyra.model.adapter.base import get_embedding_adapter, embedding_adapters, AdapterEntry

    print(f"Number of registered embedding adapters: {len(embedding_adapters)}")
    
    # List all registered adapters for debugging
    for i, entry in enumerate(embedding_adapters):
        print(f"Adapter {i}: {entry.model_adapter} (Type: {type(entry.model_adapter)})")

    # Test 1: Check if we can get an adapter for 'text2vec' with provider 'hf'
    print("\n--- Test 1: get_embedding_adapter('hf', model_name='text2vec') ---")
    adapter = get_embedding_adapter("hf", False, model_name="text2vec")
    if adapter:
        print(f"SUCCESS: Found adapter: {adapter}")
    else:
        print("FAILURE: No adapter found for text2vec")

    # Test 2: Check standard HF model
    print("\n--- Test 2: get_embedding_adapter('hf', model_name='sentence-transformers/all-mpnet-base-v2') ---")
    adapter_hf = get_embedding_adapter("hf", False, model_name="sentence-transformers/all-mpnet-base-v2")
    if adapter_hf:
        print(f"SUCCESS: Found adapter: {adapter_hf}")
    else:
        print("FAILURE: No adapter found for HF default")

except ImportError as e:
    print(f"ImportError: {e}")
except Exception as e:
    print(f"An error occurred: {e}")
    import traceback
    traceback.print_exc()
