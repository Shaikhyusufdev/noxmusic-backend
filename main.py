from fastapi import FastAPI
import yt_dlp

app = FastAPI()

@app.get("/")
async def root():
    return {"status": "NoxMusic API running!"}

@app.get("/stream")
async def get_stream(url: str):
    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Direct URL nikalo
            stream_url = None
            if 'url' in info:
                stream_url = info['url']
            elif 'formats' in info:
                # Best audio format lo
                for f in reversed(info['formats']):
                    if f.get('acodec') != 'none' and f.get('url'):
                        stream_url = f['url']
                        break

            return {
                "title": info.get('title', 'Unknown'),
                "duration": info.get('duration', 0),
                "thumbnail": info.get('thumbnail', ''),
                "stream_url": stream_url
            }
    except Exception as e:
        return {"error": str(e)}
