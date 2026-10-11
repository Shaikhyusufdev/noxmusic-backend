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

            # Agar playlist ya nested hai toh pehla entry lo
            if 'entries' in info:
                info = info['entries'][0]

            stream_url = None

            # Direct URL check karo
            if info.get('url'):
                stream_url = info['url']
            
            # Formats se best audio nikalo
            elif info.get('formats'):
                for f in reversed(info['formats']):
                    if (f.get('acodec') != 'none' 
                        and f.get('vcodec') == 'none' 
                        and f.get('url')):
                        stream_url = f['url']
                        break
                
                # Sirf audio nahi mila toh any format lo
                if not stream_url:
                    for f in reversed(info['formats']):
                        if f.get('url'):
                            stream_url = f['url']
                            break

            return {
                "title": str(info.get('title', 'Unknown')),
                "duration": int(info.get('duration', 0)),
                "thumbnail": str(info.get('thumbnail', '')),
                "stream_url": str(stream_url) if stream_url else None
            }

    except Exception as e:
        return {"error": str(e)}
