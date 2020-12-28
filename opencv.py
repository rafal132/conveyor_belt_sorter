import cv2
from msgmaker import msgcatch, msgsweep, msgdrive
import numpy as np
import serial, time
from pynput import keyboard
from pynput.keyboard import Key
from win32api import GetSystemMetrics
from numpy import interp
from object_tracking import CentroidTracker, TrackableObject

s_width = int(GetSystemMetrics(0))
s_height = int(GetSystemMetrics(1))
print(s_width,s_height)

cap = cv2.VideoCapture(0)

arduino = serial.Serial('COM6', 9600, timeout=.1)
time.sleep(1)

speed = 120
drive_step = 10
servo_step = 5
servo_bottom_limit = 55
sweep_bottom_limit = 65
servo_top_limit = 160
sweep_top_limit = 170
bot_servo = servo_bottom_limit
top_servo = servo_bottom_limit

# Callibration flags and counters:
servo_counter = servo_top_limit
callibration_top = True
callibration_bot = False
callibration = True
catched = False
moved = False
pause = True
pushed = False

# Other flags and counters:
full_pallet_counter = 0
pallet_counter_limit = 10
pallet_full = False
last_speed = speed
fps_counter = 0

# Setting up regions of interest and stuff:
y1 = 138
y2 = 350
x1 = 0
x2 = s_width
roi_height = y2-y1

pallet_edge = 180
catch_point = 235
scan_egde = 450
min_width = 16
# offset = 5

# End ROI setup

contour_list = []
placing = []

bot_servo_range = {'min_range':0,'max_range':0, 'space_left': 0}
top_servo_range = {'min_range':0,'max_range':0, 'space_left': 0}

arduino.write(bytes('<1' + msgdrive(speed) + '>' + '\n', "utf-8"))
arduino.write(bytes('<2' + msgcatch(bot_servo,top_servo) + '>' + '\n', "utf-8"))
arduino.write(bytes('<2' + msgsweep(servo_bottom_limit) + '>' + '\n', "utf-8"))

# servo warm-up
for a in range(2):
    arduino.write(bytes('<2' + msgcatch(servo_top_limit,servo_bottom_limit) + '>' + '\n', "utf-8"))
    arduino.write(bytes('<3' + msgsweep(sweep_top_limit) + '>' + '\n', "utf-8"))
    time.sleep(0.5)
    arduino.write(bytes('<2' + msgcatch(servo_bottom_limit, servo_top_limit) + '>' + '\n', "utf-8"))
    arduino.write(bytes('<3' + msgsweep(sweep_bottom_limit) + '>' + '\n', "utf-8"))
    time.sleep(0.5)
    
# end servo warm-up


# manual steering setup:
def on_press(key):
    global speed,pause, bot_servo, top_servo
    if key == Key.up:
        if speed < (180-drive_step) and pause is False:
            speed += drive_step
            arduino.write(bytes('<1' + msgdrive(speed) + '>' + '\n', "utf-8"))
            print(f"prędkość: {speed}.")
        elif speed < (180-drive_step) and pause is True:
            speed += drive_step
            print(f"prędkość: {speed}.")
        else:
            print("Osiągnięto prędkość maksymalną: 180.")
    elif key == Key.down:
        if speed > (0 + drive_step) and pause is False:
            speed -= drive_step
            arduino.write(bytes('<1' + msgdrive(speed) + '>' + '\n', "utf-8"))
            print(f"prędkość: {speed}.")
        elif speed > (0 + drive_step) and pause is True:
            speed -= drive_step
            print(f"prędkość: {speed}.")
        else:
            print("Osiągnięto prędkość maksymalną: 180.")
    elif key == Key.left:
        if speed <= 90:
            arduino.write(bytes('<1' + str(90 + abs(90 - speed)) + '>' + '\n', "utf-8"))
            print(f"prędkość: {90 + abs(90 - speed)}.")
        else:
            arduino.write(bytes('<1' + str(speed) + '>' + '\n', "utf-8"))
            print(f"prędkość: {speed}.")
    elif key == Key.right:
        if speed >= 90:
            arduino.write(bytes('<1' + str(90 - abs(90 - speed)) + '>' + '\n', "utf-8"))
            print(f"prędkość: {90 - abs(90 - speed)}.")
        else:
            arduino.write(bytes('<1' + msgdrive(speed) + '>' + '\n', "utf-8"))
            print(f"prędkość: {speed}.")
    elif key == Key.space and pause is False:
        pause = True
        arduino.write(bytes('<1090>' + '\n', "utf-8"))
        arduino.write(bytes('<2' + msgcatch(servo_bottom_limit, servo_bottom_limit) + '>' + '\n', "utf-8"))
        print(f"prędkość: {speed}. Zatrzymano.")
    elif key == Key.space and pause is True:
        pause = False
        arduino.write(bytes('<1' + msgdrive(speed) + '>' + '\n', "utf-8"))
        print(f"prędkość: {speed}. Wznowiono działanie.")
    elif key == keyboard.KeyCode(char='r') and bot_servo < servo_top_limit:
        bot_servo += servo_step
        arduino.write(bytes('<2' + msgcatch(bot_servo,top_servo) + '>' + '\n', "utf-8"))
        print(f"Dolne serwo: {bot_servo}.Do szczytu: {bot_servo_range.get('space_left')}")
    elif key == keyboard.KeyCode(char='f') and bot_servo > servo_bottom_limit:
        bot_servo -= servo_step
        arduino.write(bytes('<2' + msgcatch(bot_servo,top_servo) + '>' + '\n', "utf-8"))
        print(f"Dolne serwo: {bot_servo}.Do szczytu: {bot_servo_range.get('space_left')}")
    elif key == keyboard.KeyCode(char='t') and top_servo < servo_top_limit:
        top_servo += servo_step
        arduino.write(bytes('<2' + msgcatch(bot_servo,top_servo) + '>' + '\n', "utf-8"))
        print(f"Górne serwo: {top_servo}. Do szczytu: {top_servo_range.get('space_left')}")
    elif key == keyboard.KeyCode(char='g') and top_servo > servo_bottom_limit:
        top_servo -= servo_step
        arduino.write(bytes('<2' + msgcatch(bot_servo,top_servo) + '>' + '\n', "utf-8"))
        print(f"Górne serwo: {top_servo}.Do szczytu: {top_servo_range.get('space_left')}")


def on_release(key):
    if key == Key.left or key == Key.right:
        arduino.write(bytes('<1090>' + '\n', "utf-8"))


listener = keyboard.Listener(
    on_press=on_press,
    on_release=on_release)
listener.start()

# End manual steering setup.


# Trackbars setup:
def empty(a):
    pass


cv2.namedWindow("Parameters")
cv2.resizeWindow("Parameters",640,240)
cv2.createTrackbar("Threshold1","Parameters",200,255,empty)
cv2.createTrackbar("Threshold2","Parameters",80,255,empty)
cv2.createTrackbar("Area","Parameters",500,40000,empty)
# End Trackbars setup


# Function for displaying multiple images in one window. Useful for monitoring image processing:
def stackImages(scale,imgArray):
    rows = len(imgArray)
    cols = len(imgArray[0])
    rowsAvailable = isinstance(imgArray[0], list)
    width = imgArray[0][0].shape[1]
    height = imgArray[0][0].shape[0]
    if rowsAvailable:
        for x in range(0, rows):
            for y in range(0, cols):
                if imgArray[x][y].shape[:2] == imgArray[0][0].shape[:2]:
                    imgArray[x][y] = cv2.resize(imgArray[x][y], (0, 0), None, scale, scale)
                else:
                    imgArray[x][y] = cv2.resize(imgArray[x][y], (imgArray[0][0].shape[1], imgArray[0][0].shape[0]), None, scale, scale)
                if len(imgArray[x][y].shape) == 2:
                    imgArray[x][y] = cv2.cvtColor(imgArray[x][y], cv2.COLOR_GRAY2BGR)
        imageBlank = np.zeros((height, width, 3), np.uint8)
        hor = [imageBlank]*rows
        hor_con = [imageBlank]*rows
        for x in range(0, rows):
            hor[x] = np.hstack(imgArray[x])
        ver = np.vstack(hor)
    else:
        for x in range(0, rows):
            if imgArray[x].shape[:2] == imgArray[0].shape[:2]:
                imgArray[x] = cv2.resize(imgArray[x], (0, 0), None, scale, scale)
            else:
                imgArray[x] = cv2.resize(imgArray[x], (imgArray[0].shape[1], imgArray[0].shape[0]), None,scale, scale)
            if len(imgArray[x].shape) == 2:
                imgArray[x] = cv2.cvtColor(imgArray[x], cv2.COLOR_GRAY2BGR)
        hor = np.hstack(imgArray)
        ver = hor
    return ver


# Function for detecting and displaying contours. It returns a list of contours([x, y, width, height])
def getContours(roi, img_to_disp, draw=True, min_width=min_width):
    global callibration
    contour_list = []
    contours, hierarchy = cv2.findContours(roi, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)

    for cnt in contours:
        x0, y0, w0, h0 = cv2.boundingRect(cnt)
        area = cv2.contourArea(cnt)
        areaMin = cv2.getTrackbarPos("Area", "Parameters")
        if callibration:
            areaMin = 0
        if area > areaMin and w0 > min_width:  # and h0 > 10: # and h0 < (roi_height-20)and w0 > min_width
            peri = cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
            x, y, w, h = cv2.boundingRect(approx)
            if draw:
                cv2.drawContours(img_to_disp, cnt, -1, (0, 255, 255), 2)
                cv2.rectangle(img_to_disp, (x, y), (x + w, y + h), (255, 255, 0), 1)
            contour_list.append([x, y, w, h])
    return contour_list


# For sorting list by x:
def sortByX(elem):
    return elem[0]

timer = time.time()

# Gotta go fast:
start_time = time.time()

while True:
    fps_counter += 1
    success, img = cap.read()
    img_pallet = img.copy()
    trackers = []

    # Setting up regions of interest:
    roi = img[y1:y2, x1:x2]
    cv2.rectangle(img, (x1, y1), (x2, y2), (255, 0, 0), 1)

    # End ROI setup

    roiCopy = roi.copy()

    imgBlur = cv2.GaussianBlur(roi, (7, 7), 1)
    imgGray = cv2.cvtColor(imgBlur, cv2.COLOR_BGR2GRAY)
    threshold1 = cv2.getTrackbarPos("Threshold1", "Parameters")
    threshold2 = cv2.getTrackbarPos("Threshold2", "Parameters")
    imgCanny = cv2.Canny(imgGray, threshold1, threshold2)
    kernel = np.ones((5, 5))
    imgDil = cv2.dilate(imgCanny, kernel, iterations=1)

    contour_list = getContours(imgDil, roi, draw=False)

    if servo_counter > servo_bottom_limit and callibration_top and callibration:
        arduino.write(bytes('<2' + msgcatch(bot_servo, servo_counter) + '>' + '\n', "utf-8"))
        time.sleep(0.15)
        if servo_counter == servo_top_limit and contour_list:
            top_servo_range.update({'max_range': servo_counter})
            top_servo_range.update({'space_left': roi_height-contour_list[0][3]})
            servo_counter = servo_bottom_limit + 20
        if any(pallet_edge + 100 > contour[0] > pallet_edge for contour in contour_list):
            top_servo_range.update({'min_range': servo_counter})
        servo_counter -= 1
        if servo_counter == servo_bottom_limit:
            callibration_top = False
            callibration_bot = True
            servo_counter = servo_top_limit + 1
            arduino.write(bytes('<2' + msgcatch(servo_counter, servo_bottom_limit) + '>' + '\n', "utf-8"))
            time.sleep(0.5)
            print(top_servo_range)

    if servo_counter > servo_bottom_limit and callibration_bot and callibration:
        arduino.write(bytes('<2' + msgcatch(servo_counter, servo_bottom_limit) + '>' + '\n', "utf-8"))
        time.sleep(0.15)
        if servo_counter == servo_top_limit and contour_list:
            bot_servo_range.update({'max_range': servo_counter})
            bot_servo_range.update({'space_left': contour_list[0][1]})
            servo_counter = servo_bottom_limit + 20
        if contour_list:
            bot_servo_range.update({'min_range': servo_counter})
        servo_counter -= 1
        if servo_counter == servo_bottom_limit:
            arduino.write(bytes('<2' + msgcatch(servo_bottom_limit, servo_bottom_limit) + '>' + '\n', "utf-8"))
            callibration_bot = False
            callibration = False
            print(bot_servo_range)

    cv2.line(img, (pallet_edge,y1),(pallet_edge,y2), (0,0,255), 1)
    cv2.line(roiCopy, (pallet_edge,0),(pallet_edge,roi_height), (0,0,255), 1)
    # cv2.line(img, (catch_point,y1),(catch_point,y2), (0,0,255), 3)

    set_blocks = []
    candidates_to_place = []
    to_place = []
    contour_list.sort(key=sortByX)
    for contour in contour_list:
        if contour[0] < pallet_edge:
            set_blocks.append(contour)
        else:
            candidates_to_place.append(contour)
    # filter out tappets from candidates:
    for contour in candidates_to_place:
        if contour[1] != 0 and (contour[1]+contour[3]) < roi_height:
            to_place.append(contour)
    set_blocks.sort(key=sortByX)
    to_place.sort(key=sortByX)

    while to_place and not callibration:
        if len(set_blocks) == 0:
            placing = [0,roi_height-to_place[0][3],to_place[0][2], roi_height]
            break
        step = 0
        x, y, w, h = to_place[0]
        while step < pallet_edge:
            highest_contour = roi_height
            imgCopy = img_pallet.copy()
            pallet_roi = imgCopy[y1:y2, step:pallet_edge]
            imgBlur1 = cv2.GaussianBlur(pallet_roi, (7, 7), 1)
            imgGray1 = cv2.cvtColor(imgBlur1, cv2.COLOR_BGR2GRAY)
            imgCanny1 = cv2.Canny(imgGray1, threshold1, threshold2)
            kernel1 = np.ones((5, 5))
            imgDil1 = cv2.dilate(imgCanny1, kernel, iterations=1)
            contours_placed = getContours(imgDil1, pallet_roi, draw=True, min_width=0)
            if len(contours_placed) == 0:
                step += min_width
                placing = [step,roi_height-h,step + w,roi_height]
                highest_contour = roi_height
                break
            for contour in contours_placed:
                contour[0] += step
                if contour[1] < highest_contour:
                    highest_contour = contour[1]
            if highest_contour < h:
                step += 2  # Icrease this value to increase speed of procesing, decrease to increase precision
            else:
                # cv2.line(img,(step, y1), (step, y2), (0,0,255), 1)
                placing = [step,  highest_contour - h, step + w, highest_contour]
                break
        break

    if placing and to_place and not pause:
        cv2.rectangle(img, (placing[0], y1 + placing[1]), (placing[2], y1 + placing[3]), (0, 255, 0), 3)
        if placing[2] > pallet_edge:  # simple method for checking if pallet is full:
            full_pallet_counter += 1
            if full_pallet_counter > pallet_counter_limit:
                pallet_full = True
        else:
            full_pallet_counter = 0
            pallet_full = False

    if pallet_full:
        if not pushed:
            timer = time.time()
            pushed = True
        pause = True
        print('pause true')
        if not to_place:
            full_pallet_counter = 0
            pallet_full = False
            print('pallet full false')
        if time.time() - timer < 1:
            print('timer is LESS then 1')
            arduino.write(bytes('<1090>' + '\n', "utf-8"))
            arduino.write(bytes('<2' + msgcatch(servo_bottom_limit, servo_bottom_limit) + '>' + '\n', "utf-8"))
            arduino.write(bytes('<3' + msgsweep(sweep_top_limit) + '>' + '\n', "utf-8"))
        text = 'PALLET IS FULL'
        cv2.putText(roi, text, (20, int(roi_height / 2)),
                    cv2.FONT_HERSHEY_SIMPLEX, 2.5, (0, 0, 255), 4)
        cv2.putText(roiCopy, text, (20, int(roi_height / 2)),
                    cv2.FONT_HERSHEY_SIMPLEX, 2.5, (0, 0, 255), 4)
        if 2 > time.time() - timer > 1:
            print('timer is MORE than 1')
            arduino.write(bytes('<3' + msgsweep(sweep_bottom_limit) + '>' + '\n', "utf-8"))
        if time.time() - timer > 2:
            print('timer is MORE than 2')
            pause = False
            full_pallet_counter = 0
            pallet_full = False
            pushed = False
            arduino.write(bytes('<1' + msgdrive(speed) + '>' + '\n', "utf-8"))

    catch = 14
    bot_range = [bot_servo_range.get("min_range"), bot_servo_range.get("max_range")]
    top_range = [top_servo_range.get("min_range"), top_servo_range.get("max_range")]
    if to_place and not catched and not moved and not pause and not pallet_full:
        bot_servo_pos = int(interp(to_place[0][1] + to_place[0][3], [0, roi_height], [bot_range[1], bot_range[0]]))
        top_servo_pos = int(interp(to_place[0][1], [0, roi_height], [top_range[0], top_range[1]]))
        if to_place[0][0] <= (catch_point + 0.15*speed) and not catched:
            arduino.write(bytes('<2' + msgcatch(bot_servo_pos + catch, top_servo_pos + catch) + '>' + '\n', "utf-8"))
            catched = True
            timer = time.time()
        elif to_place[0][0] and not catched:
            arduino.write(bytes('<2' + msgcatch(bot_servo_pos, top_servo_pos) + '>' + '\n', "utf-8"))

    if catched and time.time() - timer > 0.4 and not moved and not pause and not pallet_full:
        print(time.time()-timer)
        bot_servo_pos = int(interp(placing[3], [0, roi_height], [bot_range[1], bot_range[0]]))
        top_servo_pos = int(interp(placing[1], [0, roi_height], [top_range[0], top_range[1]]))
        if placing[3] == roi_height:
            bot_catch = 0
            top_catch = 1.5*catch
            bot_servo_pos = servo_bottom_limit
            print("bottom position")
        elif placing[1] < 15:
            bot_catch = 2 * catch
            top_catch = 0

            top_servo_pos = servo_bottom_limit
            bot_servo_pos = servo_top_limit
            print("top position")
        else:
            bot_catch = catch
            top_catch = catch
            print("some else position")

        arduino.write(bytes('<2' + msgcatch(bot_servo_pos + bot_catch, top_servo_pos + top_catch) + '>' + '\n', "utf-8"))
        moved = True

    if catched and time.time() - timer > 0.8 and moved and not pause and not pallet_full:
        print(time.time() - timer)
        arduino.write(bytes('<2' + msgcatch(servo_bottom_limit, servo_bottom_limit) + '>' + '\n', "utf-8"))
        print("open catch")
        catched = False

    if time.time() - timer > 2 and moved and not pause and not pallet_full:
        moved = False

    imgStack = stackImages(1, ([roi, imgGray, imgCanny], [imgCanny, imgDil, roi]))

    if not callibration:
        cv2.imshow("Full Conveyor Belt",img)
        cv2.imshow("Conveyor Belt", roiCopy)
        cv2.imshow('Image processing', imgStack)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        arduino.write(bytes('<1' + str(90) + '>' + '\n', "utf-8"))
        arduino.write(bytes('<2' + msgcatch(servo_bottom_limit, servo_bottom_limit) + '>' + '\n', "utf-8"))
        break
finish_time = time.time()
fps = fps_counter / (finish_time-start_time)
print('Frames per second: ' + str(fps))
cap.release()
