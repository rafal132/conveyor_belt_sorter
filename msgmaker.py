
def msgcatch(bot_servo, top_servo):
    if bot_servo < 100:
        msg_bot = '0' + str(bot_servo)
    else:
        msg_bot = str(bot_servo)
    if top_servo < 100:
        msg_top = '0' + str(top_servo)
    else:
        msg_top = str(top_servo)
    msg = msg_bot + msg_top

    return msg


def msgsweep(sweep_servo):
    if sweep_servo < 100:
        msg = '0' + str(sweep_servo)
    else:
        msg = str(sweep_servo)

    return msg

def msgdrive(drive_servo):
    if drive_servo < 100:
        msg = '0' + str(drive_servo)
    else:
        msg = str(drive_servo)

    return msg




