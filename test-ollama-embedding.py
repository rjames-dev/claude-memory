#!/usr/bin/env python3
"""
Test script to verify Ollama embedding generation works correctly.

This tests:
1. Connection to Ollama
2. Embedding generation with mxbai-embed-large
3. Vector dimensions and format
"""

import requests
import json
import sys

OLLAMA_URL = "http://localhost:11434"
MODEL = "mxbai-embed-large"

def test_ollama_connection():
    """Test if Ollama is running and accessible."""
    print("Testing Ollama connection...")
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags")
        if response.status_code == 200:
            models = response.json().get('models', [])
            print(f"✅ Connected to Ollama")
            print(f"   Available models: {len(models)}")

            # Check if our embedding model is available
            model_names = [m.get('name', '') for m in models]
            if any(MODEL in name for name in model_names):
                print(f"✅ {MODEL} model found")
                return True
            else:
                print(f"❌ {MODEL} model not found")
                print(f"   Available: {model_names}")
                return False
        else:
            print(f"❌ Ollama returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Failed to connect to Ollama: {e}")
        return False


def generate_embedding(text):
    """Generate embedding for given text."""
    print(f"\nGenerating embedding for: '{text}'")
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/embeddings",
            json={
                "model": MODEL,
                "prompt": text
            },
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            embedding = data.get('embedding', [])

            if embedding:
                print(f"✅ Embedding generated successfully")
                print(f"   Dimensions: {len(embedding)}")
                print(f"   First 5 values: {embedding[:5]}")
                print(f"   Vector type: {type(embedding)}")
                return embedding
            else:
                print(f"❌ No embedding in response")
                return None
        else:
            print(f"❌ Request failed with status {response.status_code}")
            print(f"   Response: {response.text}")
            return None

    except Exception as e:
        print(f"❌ Error generating embedding: {e}")
        return None


def test_similar_phrases():
    """Test that similar phrases have similar embeddings."""
    print("\n" + "="*80)
    print("Testing semantic similarity...")
    print("="*80)

    phrases = [
        "check database health",
        "verify database status",
        "show git status",
        "list docker containers"
    ]

    embeddings = {}
    for phrase in phrases:
        emb = generate_embedding(phrase)
        if emb:
            embeddings[phrase] = emb

    # Calculate cosine similarity
    if len(embeddings) >= 2:
        print("\nCalculating similarities...")

        def cosine_similarity(v1, v2):
            """Calculate cosine similarity between two vectors."""
            import math
            dot_product = sum(a * b for a, b in zip(v1, v2))
            magnitude1 = math.sqrt(sum(a * a for a in v1))
            magnitude2 = math.sqrt(sum(b * b for b in v2))
            return dot_product / (magnitude1 * magnitude2)

        # Compare first two database-related phrases
        db_phrases = list(embeddings.keys())[:2]
        if len(db_phrases) == 2:
            sim = cosine_similarity(embeddings[db_phrases[0]], embeddings[db_phrases[1]])
            print(f"\nSimilarity between:")
            print(f"  '{db_phrases[0]}'")
            print(f"  '{db_phrases[1]}'")
            print(f"  Similarity: {sim:.4f}")

            if sim > 0.7:
                print(f"✅ High similarity detected (both about database)")
            else:
                print(f"⚠️  Lower similarity than expected")


def main():
    print("="*80)
    print("Ollama Embedding Generation Test")
    print("="*80)

    # Test 1: Connection
    if not test_ollama_connection():
        print("\n❌ Cannot proceed without Ollama connection")
        sys.exit(1)

    # Test 2: Basic embedding generation
    embedding = generate_embedding("Hello, this is a test phrase")

    if not embedding:
        print("\n❌ Embedding generation failed")
        sys.exit(1)

    # Test 3: Expected dimensions for mxbai-embed-large
    expected_dim = 1024  # mxbai-embed-large produces 1024-dimensional vectors
    if len(embedding) == expected_dim:
        print(f"\n✅ Embedding has expected dimensions ({expected_dim})")
    else:
        print(f"\n⚠️  Unexpected dimensions: {len(embedding)} (expected {expected_dim})")

    # Test 4: Semantic similarity
    test_similar_phrases()

    print("\n" + "="*80)
    print("All tests completed!")
    print("="*80)


if __name__ == '__main__':
    main()
