#!/usr/bin/env python3
"""
Generate 384-dimensional embeddings using sentence-transformers
Compatible with OpenWebUI's RAG_EMBEDDING_MODEL configuration
"""

import sys
import json
from sentence_transformers import SentenceTransformer

# Load the model (same as OpenWebUI uses)
MODEL_NAME = 'sentence-transformers/all-MiniLM-L6-v2'

try:
    model = SentenceTransformer(MODEL_NAME)
except Exception as e:
    print(json.dumps({"error": f"Failed to load model: {str(e)}"}), file=sys.stderr)
    sys.exit(1)

def generate_embedding(text):
    """Generate embedding for given text"""
    try:
        # Generate embedding
        embedding = model.encode(text)

        # Convert to list for JSON serialization
        embedding_list = embedding.tolist()

        # Verify dimensions
        if len(embedding_list) != 384:
            raise ValueError(f"Expected 384 dimensions, got {len(embedding_list)}")

        return {
            "success": True,
            "embedding": embedding_list,
            "dimensions": len(embedding_list),
            "model": MODEL_NAME
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

if __name__ == "__main__":
    # Read text from stdin or command line argument
    if len(sys.argv) > 1:
        text = " ".join(sys.argv[1:])
    else:
        text = sys.stdin.read().strip()

    if not text:
        print(json.dumps({"error": "No input text provided"}))
        sys.exit(1)

    # Generate and output embedding
    result = generate_embedding(text)
    print(json.dumps(result))

    sys.exit(0 if result.get("success") else 1)
