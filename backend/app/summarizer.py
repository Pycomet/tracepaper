# backend/app/summarizer.py

from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM # type: ignore
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Global variable to hold the summarization pipeline
# Initialize to None, and load it on demand or during app startup
summarizer_pipeline = None
MODEL_NAME = "google/flan-t5-base"

# Define a cache directory for models within the backend/data directory if possible
# This helps in environments where the default Hugging Face cache might not be persistent (e.g. some Docker setups)
# Ensure this path is writable by the application
MODEL_CACHE_DIR = Path(__file__).parent.parent / "data" / "hf_models_cache"

def initialize_summarizer():
    global summarizer_pipeline
    if summarizer_pipeline is None:
        logger.info(f"Initializing summarization pipeline with model: {MODEL_NAME}...")
        try:
            # Ensure the cache directory exists before trying to use it
            MODEL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
            
            # Load tokenizer and model with a specified cache directory
            tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, cache_dir=MODEL_CACHE_DIR)
            model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME, cache_dir=MODEL_CACHE_DIR)
            
            # Ensure the model is in evaluation mode (important for some models, good practice)
            model.eval()

            # For CPU, explicitly move model to CPU if not already. 
            # device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            # model.to(device) # Transformers pipeline handles device placement by default but can be explicit.
            
            summarizer_pipeline = pipeline(
                "summarization", 
                model=model, 
                tokenizer=tokenizer,
                # device=-1 for CPU explicitly, or let pipeline choose. 
                # Forcing CPU if that's the explicit goal.
                device=-1 
            )
            logger.info("Summarization pipeline initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize summarization pipeline: {e}", exc_info=True)
            # Depending on strategy, could raise error or leave pipeline as None
            raise

def generate_summary(text: str, max_length: int = 150, min_length: int = 30) -> str:
    if summarizer_pipeline is None:
        logger.warning("Summarizer pipeline not initialized. Attempting to initialize now.")
        try:
            initialize_summarizer() 
        except Exception as e:
            logger.error(f"Failed to initialize summarizer during on-demand attempt: {e}", exc_info=True)
            # Fall through to the check below, which will see pipeline is still None
        
        if summarizer_pipeline is None: # Check again after attempt
             logger.error("Failed to generate summary because pipeline could not be initialized.")
             return "Error: Summarization service not available."

    logger.info(f"Generating summary for text of length {len(text)} chars...")
    try:
        # Flan-T5 and similar models often benefit from a prefix indicating the task.
        # For summarization, a common prefix is "summarize: ".
        # However, the `summarization` pipeline might handle this automatically.
        # Testing is needed to see if adding it improves results for flan-t5 with this pipeline.
        # For now, let the pipeline handle it.
        # input_text = f"summarize: {text}" 

        summary_outputs = summarizer_pipeline(text, max_length=max_length, min_length=min_length, do_sample=False)
        summary_text = summary_outputs[0]['summary_text']
        logger.info(f"Generated summary: {summary_text[:100]}...") # Log first 100 chars
        return summary_text
    except Exception as e:
        logger.error(f"Error during summary generation: {e}", exc_info=True)
        return f"Error generating summary: {e}"

# Example of how to use (optional, for direct testing of this module):
# if __name__ == "__main__":
#     initialize_summarizer() # Initialize on module run
#     sample_text = (
#         "Preheat the oven to 350 degrees F (175 degrees C). Grease and flour a 9x9 inch pan. "
#         "In a medium bowl, cream together the sugar and butter. Beat in the eggs, one at a time, "
#         "then stir in the vanilla. Combine flour and baking powder, add to the creamed mixture "
#         "and mix well. Finally, stir in the milk until batter is smooth. Pour or spoon batter "
#         "into the prepared pan. Bake for 30 to 40 minutes in the preheated oven. For cupcakes, "
#         "bake 20 to 25 minutes. Cake is done when it springs back to the touch."
#     )
#     summary = generate_summary(sample_text)
#     print("\nSample Text:")
#     print(sample_text)
#     print("\nGenerated Summary:")
#     print(summary) 