# IDP

## RTMP processing FFMPEG

### Reference:
- [sdudio-streams-ffmpeg](https://github.com/Ikigaians/studio-streams-ffmpeg7.0.2)

### Issue

- Cannot open rtmp server in vlc

# Latest discussion with Kimi and Steve about LOS/SDP/Roulette

## LOS logic

- LOS透過SDP傳給他的game status判斷是否處於開局狀態，若不是，則屏蔽掉PUT request
- 開局狀態下，LOS若收到PUT request，則檢查是否為合法request，若合法則response，若不合法，則返回400
- LOS透過SDP傳給他的table ID,確認收到的request是屬於哪一桌的，若不是屬於該桌的request，則返回400

## SDP logic

- 如果SDP收到400的response，則需要顯示提醒on-site engineer需要進行維護的錯誤訊息

## Roulette logic

- 需要針對game protocol over RS232 protocol進行error handling, 包含timeout, checksum error, etc.
- Roulette若是出現數值傳輸錯誤，SDP則需要進行resend
- Roulette若是出現傳輸timeout的error，SDP則需要顯示提醒on-site engineer需要進行維護的錯誤訊息
- RS232是單工的所以需要設計RX/TX 