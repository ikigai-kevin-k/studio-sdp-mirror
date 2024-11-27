from typing import Optional, List, Union
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from datetime import datetime
import uvicorn

app = FastAPI()

# Define data models
class Result(BaseModel):
    roulette: Optional[str] = None
    sicBo: Optional[List[int]] = None
    baccarat: Optional[List[str]] = None

class TableRound(BaseModel):
    roundId: str
    gameCode: str
    gameType: str
    betStopTime: datetime
    status: str
    result: Result
    createdAt: datetime

class Table(BaseModel):
    gameCode: str
    gameType: str
    visibility: str
    betPeriod: int
    tableRound: TableRound

class ErrorResponse(BaseModel):
    message: str
    code: int

class ResponseModel(BaseModel):
    error: Optional[ErrorResponse] = None
    data: Optional[dict] = None

class DealRequest(BaseModel):
    roundId: str
    roulette: Optional[str] = None
    sicBo: Optional[List[int]] = None
    baccarat: Optional[List[str]] = None

class VisibilityRequest(BaseModel):
    visibility: str

# API route implementation
@app.get("/v1/service/table/{gameCode}")
async def get_table(gameCode: str):  #gameCode:SDP_001
    # simulate returning data
    return {
        "error": None,
        "data": {
            "table": {
                "gameCode": gameCode,
                "gameType": "roulette",
                "visibility": "visible",
                "betPeriod": 15,
                "tableRound": {
                    "roundId": "round-1",
                    "gameCode": gameCode,
                    "gameType": "roulette",
                    "betStopTime": datetime.now(),
                    "status": "betting",
                    "result": {
                        "roulette": "11" # last winning number
                    },
                    "createdAt": datetime.now()
                }
            }
        }
    }

@app.post("/v1/service/sdp/table/{gameCode}/login")
async def login(gameCode: str, x_sdp_token: str = Header(...)):
    return {
        "error": None,
        "data": {
            "token": "sample-token-123"
        }
    }

@app.post("/v1/service/sdp/table/{gameCode}/start")
async def start_game(gameCode: str, bearer: str = Header(...)):
    if not bearer.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return {
        "error": None,
        "data": {
            "table": {
                "gameCode": gameCode,
                "gameType": "roulette",
                "visibility": "visible",
                "betPeriod": 15,
                "tableRound": {
                    "roundId": "round-1",
                    "gameCode": gameCode,
                    "gameType": "roulette",
                    "betStopTime": datetime.now(),
                    "status": "betting",
                    "result": None,
                    "createdAt": datetime.now()
                }
            }
        }
    }

@app.post("/v1/service/sdp/table/{gameCode}/deal")
async def deal(gameCode: str, request: DealRequest, bearer: str = Header(...)):
    if not bearer.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return {
        "error": None,
        "data": {
            "table": {
                "gameCode": gameCode,
                "gameType": "roulette",
                "visibility": "visible",
                "betPeriod": 15,
                "tableRound": {
                    "roundId": request.roundId,
                    "gameCode": gameCode,
                    "gameType": "roulette",
                    "betStopTime": datetime.now(),
                    "status": "stop",
                    "result": {
                        "roulette": request.roulette,
                    },
                    "createdAt": datetime.now()
                }
            }
        }
    }

@app.post("/v1/service/sdp/table/{gameCode}/finish")
async def finish_game(gameCode: str, bearer: str = Header(...)):
    if not bearer.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return {
        "error": None,
        "data": {
            "table": {
                "gameCode": gameCode,
                "gameType": "roulette",
                "visibility": "visible",
                "betPeriod": 15,
                "tableRound": None
            }
        }
    }

@app.post("/v1/service/sdp/table/{gameCode}/visibility")
async def set_visibility(gameCode: str, request: VisibilityRequest, bearer: str = Header(...)):
    if not bearer.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return {
        "error": None,
        "data": {
            "table": {
                "gameCode": gameCode,
                "gameType": "roulette",
                "visibility": request.visibility,
                "betPeriod": 15,
                "tableRound": None
            }
        }
    }

if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000)