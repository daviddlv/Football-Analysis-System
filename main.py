import functions_framework
from cloudevents.http import CloudEvent
from google.cloud import storage

from utils import read_video, save_video
from trackers import Tracker
from team_assigner import TeamAssigner
from player_ball_assigner import PlayerBallAssigner
import numpy as np
from camera_movement_estimator import CameraMovementEstimator
from view_transformer import ViewTransformer
from speed_and_distance_estimator import SpeedAndDistanceEstimator
from pathlib import Path

@functions_framework.cloud_event
def handler(event: CloudEvent) -> None:
    """This function is triggered by a change in a storage bucket.

    Args:
        cloud_event: The CloudEvent that triggered this function.
    Returns:
        The file name of the output video.
    """
    data = event.data

    if '.avi' in data['name']:
        return data['name']
    
    input_video_path = f'input_videos/${data["name"]}'

    client = storage.Client()
    bucket = client.bucket(data['bucket'])

    source_blob = bucket.blob(data['name'])
    source_blob.download_to_filename(input_video_path)

    output_video_path = analyze(input_video_path)
    
    print(f"Upload output video : ${output_video_path}")
    dest_blob = bucket.blob(output_video_path)
    dest_blob.upload_from_filename(output_video_path)
    print("Done")

def analyze(input_video_path: str) -> str:
    print("Start analyzing")
    # Read Video
    model_path = 'models/best.pt'
    output_video_path = f'{Path(input_video_path).stem}.avi'
    video_frames = read_video(input_video_path)

    #initialize tracker 
    tracker = Tracker(model_path=model_path)

    print("Get object tracks")
    tracks = tracker.get_object_tracks(video_frames,
                                       read_from_stub=True,
                                       stub_path="stubs/track_stubs1.pkl",)
    
    # Get object positions
    print("Add position to tracks")
    tracker.add_position_to_tracks(tracks)
    
    # Camera movement estimator
    camera_movement_estimator = CameraMovementEstimator(video_frames[0])
    print("Get camera movement")
    camera_movement_per_frame = camera_movement_estimator.get_camera_movement(video_frames, 
                                                                              read_from_stub=True, 
                                                                              stub_path="stubs/camera_movement_stubs1.pkl")
    print("Add adjusted positions to tracks")
    camera_movement_estimator.add_adjust_positions_to_tracks(tracks, camera_movement_per_frame)

    # view transformer
    view_transformer = ViewTransformer()
    print("Add transformed position to tracks")
    view_transformer.add_transformed_position_to_tracks(tracks)

    #interpolate ball positions
    print("Interpolate ball positions")
    tracks['ball'] = tracker.interpolate_ball_positions(tracks["ball"])

    # Speed and Distance Estimator 
    speed_and_distance_estimator = SpeedAndDistanceEstimator()
    print("Add speed and distance to tracks")
    speed_and_distance_estimator.add_speed_and_sistance_to_tracks(tracks)

    # Assign player teams 
    team_assigner = TeamAssigner()
    print("Assign team color")
    team_assigner.assign_team_color(video_frames[0],
                                    tracks['players'][0])
    
    for frame_num, player_tracks in enumerate(tracks['players']):
        for player_id, track in player_tracks.items():
            team = team_assigner.get_player_team(video_frames[frame_num],
                                                 track['bbox'],
                                                 player_id)
            tracks['players'][frame_num][player_id]['team'] = team
            tracks['players'][frame_num][player_id]['team_color'] = team_assigner.team_color[team]

    # Assigne ball aquisition
    player_assigner = PlayerBallAssigner()
    team_ball_control = []
    for frame_num, player_track in enumerate(tracks['players']):
        ball_bbox = tracks['ball'][frame_num][1]['bbox']

        assigned_player = player_assigner.assign_ball_to_player(player_track, ball_bbox)

        if assigned_player != -1:
            tracks['players'][frame_num][assigned_player]['has_ball'] = True
            team_ball_control.append(tracks['players'][frame_num][assigned_player]['team'])
        else:
            team_ball_control.append(team_ball_control[-1])
    team_ball_control = np.array(team_ball_control)

    # Draw Output
    ## Draw object tracks
    print("Draw annotations")
    output_video_frames = tracker.draw_annotations(video_frames, tracks, team_ball_control)

    ## Draw camera movement
    print("Draw camera movement")
    output_video_frames = camera_movement_estimator.draw_camera_movement(output_video_frames, camera_movement_per_frame)

    ## Draw speed and distance
    print("Draw speed and distance")
    speed_and_distance_estimator.draw_speed_and_distance(output_video_frames, tracks)

    # Save Video
    print("Save video")
    save_video(output_video_frames, output_video_path)

    return output_video_path
    
# if __name__ == '__main__':
#     analyze('input_videos/08fd33_4.mp4')
