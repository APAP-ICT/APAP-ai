import cv2

from model.detect import estimate_distance


def test_calculate_distance():
    cap = cv2.VideoCapture("resources/person.mp4")
    assert cap.isOpened(), "Error reading video file"

    while cap.isOpened():
        success, im0 = cap.read()
        if not success:
            print("Video frame is empty or video processing has been successfully completed.")
            break

        result = estimate_distance(im0)

        cv2.imshow("Object Tracking", result.result.plot_image)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
