# IDP

## RTMP processing FFMPEG

### Reference:
- [sdudio-streams-ffmpeg](https://github.com/Ikigaians/studio-streams-ffmpeg7.0.2)

### Issue

- Cannot open rtmp server in vlc

# Latest discussion with Kimi and Steve about LOS/SDP/Roulette

## LOS logic

- [x] LOS determines whether it's in an open game state based on the game status transmitted by SDP. If not, it blocks SDP's GET request.
- [ ] During an open game state, when LOS receives a POST request from the manager, it checks if it's a valid request. If valid, it responds; if invalid, it returns a 403 error.
- [ ] LOS uses the table ID transmitted by SDP to confirm which table the received request belongs to. If the request doesn't belong to that table, it returns a 403 error.

## SDP logic

- 如果SDP收到400的response，則需要顯示提醒on-site engineer需要進行維護的錯誤訊息

## Roulette logic

- 需要針對game protocol over RS232 protocol進行error handling, 包含timeout, checksum error, etc.
- Roulette若是出現數值傳輸錯誤，SDP則需要進行resend
- Roulette若是出現傳輸timeout的error，SDP則需要顯示提醒on-site engineer需要進行維護的錯誤訊息
- RS232是單工的所以需要設計RX/TX 