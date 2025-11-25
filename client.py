import discord
from dataclasses import dataclass
from typing import Dict
@dataclass
class clients:
    tts_channel_id: int = None
    tts_voice: str = "en-US-JennyNeural" 
    stay_24_7: bool = None
    vc: discord.VoiceClient = None

class Client:
    Clients: Dict[discord.Guild, clients] = {} 



    