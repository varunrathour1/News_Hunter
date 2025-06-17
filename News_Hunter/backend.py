
import asyncio
import sys
import logging
# Configure logging at the very beginning of the script
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())



# Enable asyncio debug mode (add this line)
asyncio.get_event_loop().set_debug(True) # This might need to be called after app startup

from fastapi import FastAPI, HTTPException, File, Response
from fastapi.responses import FileResponse
import os
from pathlib import Path
from dotenv import load_dotenv
import logging
from models import NewsRequest
from utils import generate_broadcast_news, text_to_audio_elevenlabs_sdk, tts_to_audio
from news_scraper import NewsScraper
from reddit_scraper import scrape_reddit_topics

from fastapi import FastAPI, HTTPException, File, Response
from fastapi.responses import FileResponse
import os
from pathlib import Path
from dotenv import load_dotenv
import logging # Import logging module

from models import NewsRequest
from utils import generate_broadcast_news, text_to_audio_elevenlabs_sdk, tts_to_audio # Removed tts_to_audio here if not explicitly used from backend directly
from news_scraper import NewsScraper
from reddit_scraper import scrape_reddit_topics

# Configure logging at the very beginning of the script
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = FastAPI()
load_dotenv() # Load environment variables from .env file


@app.post("/generate-news-audio")
async def generate_news_audio(request: NewsRequest):
    logging.info(f"Received request for topics: {request.topics} from source: {request.source_type}")
    try:
        results = {}
        
        # --- News Scraping ---
        if request.source_type in ["news", "both"]:
            logging.info("Initiating news scraping...")
            news_scraper = NewsScraper()
            results["news"] = await news_scraper.scrape_news(request.topics)
            logging.info(f"News scraping completed. Found {len(results.get('news', {}))} topics with news data.")
        
        # --- Reddit Scraping ---
        if request.source_type in ["reddit", "both"]:
            logging.info("Initiating Reddit scraping...")
            results["reddit"] = await scrape_reddit_topics(request.topics)
            logging.info(f"Reddit scraping completed. Found {len(results.get('reddit', {}))} topics with Reddit data.")

        news_data = results.get("news", {})
        reddit_data = results.get("reddit", {})

        # Check if any data was actually collected
        if not news_data and not reddit_data:
            logging.warning("No data found from news or Reddit scraping for the given topics.")
            raise HTTPException(status_code=400, detail="No relevant data found for the given topics to generate a summary.")

        # --- Generate News Summary ---
        logging.info("Generating broadcast news summary using LLM (Anthropic)...")
        anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        if not anthropic_api_key:
            logging.error("ANTHROPIC_API_KEY environment variable is not set. Please set it to proceed.")
            raise HTTPException(status_code=500, detail="Anthropic API key is not configured. Cannot generate summary.")

        news_summary = generate_broadcast_news(
            api_key=anthropic_api_key, # Use the fetched API key
            news_data=news_data,
            reddit_data=reddit_data,
            topics=request.topics
        )

        if not news_summary:
            logging.warning("LLM (Anthropic) returned an empty or None summary.")
            raise HTTPException(status_code=500, detail="Failed to generate news summary. LLM response was empty.")
        logging.info("News summary generated successfully.")

        # --- Generate Audio ---
        logging.info("Attempting to convert news summary to audio using ElevenLabs SDK...")
        eleven_api_key = os.getenv("ELEVEN_API_KEY")
        if not eleven_api_key:
            logging.error("ELEVEN_API_KEY environment variable is not set. Cannot generate audio.")
            raise HTTPException(status_code=500, detail="ElevenLabs API key is not configured. Cannot generate audio.")

        audio_path = text_to_audio_elevenlabs_sdk(
            text=news_summary,
            voice_id="JBFqnCBsd6RMkjVDRZzb",
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128",
            output_dir="audio",
            api_key=eleven_api_key # Pass API key to the function
        )

        if not audio_path:
            logging.error("Audio generation with ElevenLabs SDK failed: returned no path.")
            raise HTTPException(status_code=500, detail="Audio generation failed. No audio file path was returned.")

        # --- Serve Audio File ---
        output_file_path = Path(audio_path)
        if output_file_path.exists() and output_file_path.stat().st_size > 0:
            logging.info(f"Audio file found and is not empty: {audio_path}. Preparing response.")
            # FastAPI's FileResponse is better for serving files
            return FileResponse(
                path=output_file_path,
                media_type="audio/mpeg",
                headers={"Content-Disposition": "attachment; filename=news-summary.mp3"}
            )
        else:
            logging.error(f"Generated audio file is missing or empty at: {audio_path}")
            raise HTTPException(status_code=500, detail="Generated audio file not found or is empty on the server.")
    
    except HTTPException as http_exc:
        # Re-raise HTTPExceptions directly, FastAPI will handle logging their details if configured
        logging.error(f"Caught HTTP Exception: Status {http_exc.status_code}, Detail: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        # Catch any other unexpected errors and log them with full traceback for debugging
        logging.error(f"An unhandled error occurred in generate_news_audio: {e}", exc_info=True)
        # Re-raise as HTTPException for consistent API error response
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {e}")


if __name__ == "__main__":
    import uvicorn
    # Make sure this port matches frontend.py's BACKEND_URL
    uvicorn.run(
        "backend:app",
        host="0.0.0.0",
        port=8000, # Frontend is configured for port 1234
        reload=True
    )

'''
app = FastAPI()
load_dotenv()


@app.post("/generate-news-audio")
async def generate_news_audio(request: NewsRequest):
    try:
        results = {}
        
        if request.source_type in ["news", "both"]:
            news_scraper = NewsScraper()
            results["news"] = await news_scraper.scrape_news(request.topics)
        
        if request.source_type in ["reddit", "both"]:
            results["reddit"] = await scrape_reddit_topics(request.topics)

        news_data = results.get("news", {})
        reddit_data = results.get("reddit", {})
        news_summary = generate_broadcast_news(
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            news_data=news_data,
            reddit_data=reddit_data,
            topics=request.topics
        )

        audio_path = text_to_audio_elevenlabs_sdk(
            text=news_summary,
            voice_id="JBFqnCBsd6RMkjVDRZzb",
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128",
            output_dir="audio"
        )

        if audio_path and Path(audio_path).exists():
            with open(audio_path, "rb") as f:
                audio_bytes = f.read()

            return Response(
                content=audio_bytes,
                media_type="audio/mpeg",
                headers={"Content-Disposition": "attachment; filename=news-summary.mp3"}
            )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend:app",
        host="0.0.0.0",
        port=1234,
        reload=True
    )

    '''