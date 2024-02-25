"""
Demonstration of the GazeTracking library.
Check the README.md for complete documentation.
"""

import cv2
from gaze_tracking import GazeTracking
#from spotify import Song, Spotify
#INTERVAL = 30
gaze = GazeTracking()
webcam = cv2.VideoCapture(1)
focused, distracted = 0, 0
'''list_of_genres = ["pop rap", "pop", "edm", "electro house"]
ratios_of_productivity = []
for genre in list_of_genres: #get a list of songs for each genre and play them for 5 min
    songs = []
    time = 0
    focused, distracted = 0, 0
    while time < INTERVAL:
        #curr = Song(genre)
        #songs.append(curr)
        #time += curr.length
        
        while True:
            # We get a new frame from the webcam
            _, frame = webcam.read()
            
            # We send this frame to GazeTracking to analyze it
            gaze.refresh(frame)

            frame = gaze.annotated_frame()
            text = ""
            
            if gaze.is_right() or gaze.is_left() or gaze.is_up() or gaze.is_center():
                text = "GIT BACK TO WORK"
                distracted += 1
                if focused > 3000:
                    distracted = 0
            else:
                text = "Focused"
                focused += 1
                if distracted > 3000: 
                    focused = 0
            

            cv2.putText(frame, text, (90, 60), cv2.FONT_HERSHEY_DUPLEX, 1.6, (147, 58, 31), 2)

            left_pupil = gaze.pupil_left_coords()
            right_pupil = gaze.pupil_right_coords()
            cv2.putText(frame, "Left pupil:  " + str(left_pupil), (90, 130), cv2.FONT_HERSHEY_DUPLEX, 0.9, (147, 58, 31), 1)
            cv2.putText(frame, "Right pupil: " + str(right_pupil), (90, 165), cv2.FONT_HERSHEY_DUPLEX, 0.9, (147, 58, 31), 1)

            cv2.imshow("Demo", frame)
            
    ratios_of_productivity.append(focused / (focused+distracted))'''
   
while True:
            # We get a new frame from the webcam
    _, frame = webcam.read()
            
            # We send this frame to GazeTracking to analyze it
    gaze.refresh(frame)

    frame = gaze.annotated_frame()
    text = ""
            
    if gaze.is_right() or gaze.is_left() or gaze.is_up() or gaze.is_center():
        text = "GIT BACK TO WORK"
        distracted += 1
        if focused > 3000:
            distracted = 0
    else:
        text = "Focused"
        focused += 1
        if distracted > 3000: 
            focused = 0
            

    cv2.putText(frame, text, (90, 60), cv2.FONT_HERSHEY_DUPLEX, 1.6, (147, 58, 31), 2)

    left_pupil = gaze.pupil_left_coords()
    right_pupil = gaze.pupil_right_coords()
    cv2.putText(frame, "Left pupil:  " + str(left_pupil), (90, 130), cv2.FONT_HERSHEY_DUPLEX, 0.9, (147, 58, 31), 1)
    cv2.putText(frame, "Right pupil: " + str(right_pupil), (90, 165), cv2.FONT_HERSHEY_DUPLEX, 0.9, (147, 58, 31), 1)

    cv2.imshow("Demo", frame)
    if cv2.waitKey(1) == 27:
        break
webcam.release()
cv2.destroyAllWindows()
