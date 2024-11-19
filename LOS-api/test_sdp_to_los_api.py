"""
sdp game start:      //visibility => enabled

(cost 8.5 sec)

sdp place bet :      send /start api to LOS => open                                         
(cost 10.5 sec)
sdp ball launch :    do nothing to LOS
(cost 8 sec)
sdp no more bet :    do nothing to LOS => auto bet stop (LOS set betperiod =15 sec by default)
(cost 21.5 sec)
sdp winning number : send /deal api to LOS => result 
                     send /finish api to LOS

table close :        //visibility => disabled


if warning flag/error code of state machine occurs, send deal api with "roulette"(result) = -1
then send finish and set visability =  invisible
after trouble solved, set visability = visible and resume the normal flow as above

"""
sdp_num = 'SDP-001'
visible = True
while visible:

    if first_time_login:
        token = send_login_api_to_LOS(sdp)

    state = 'game_start'
    send_visable_api_to_LOS(sdp_num,token)
    sleep(8.5)
    
    
    state = 'place_bet'
    send_start_api_to_LOS(sdp_num,token)
    sleep(10.5)

    try:
        state = 'ball_launch'
        # do nothing
        sleep(8)

        state = 'no_more_bet'
        sleep(21.5)

        state = 'winning_number'
        send_deal_api_to_LOS(sdp_num,token,winning_number)
        sleep(2) 
        send_finish_api_to_LOS(sdp_num,token)

    except Exception as e:
        print(e)
        send_deal_api_to_LOS(sdp_num,token,-1)
        send_finish_api_to_LOS(sdp_num,token)
        visible = False





