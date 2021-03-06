import os
import glob
import psycopg2
import pandas as pd
from sql_queries import *


def process_song_file(cur, filepath):
    """
        Takes a filepath to read the song file and populate the song and artist record dimension tables
    """
    # open song file
    df = pd.read_json(filepath, lines=True)

    # insert song record
    song_data =  df[
        ["song_id", "title", "artist_id", "year", "duration"]
    ].values.tolist()[0]
    cur.execute(song_table_insert, song_data)
    
    # insert artist record
    artist_data =  df[
        ["artist_id", "artist_name", "artist_location", "artist_latitude", "artist_longitude"]
    ].values.tolist()[0]
    cur.execute(artist_table_insert, artist_data)


def process_log_file(cur, filepath):
    """
        Takes a filepath to read the log file and populate the songplay fact table, and dimension tables time and users
    """
    # open log file
    df = pd.read_json(filepath, lines=True)
    df["start_time"] = pd.to_datetime(df["ts"], unit="ms")

    # filter by NextSong action
    df = df[df["page"] == "NextSong"]

    # convert timestamp column to datetime
    t = df["start_time"].drop_duplicates()
    
    # insert time data records
    column_labels = ["hour", "day", "weekofyear", "month", "year", "dayofweek"]
    time_data = (getattr(t.dt, column).rename(column) for column in column_labels)
    time_df = t.to_frame("start_time").join(pd.concat(time_data, axis=1))

    for i, row in time_df.iterrows():
        cur.execute(time_table_insert, list(row))

    # load user table
    user_df = df[
        ["userId", "firstName", "lastName", "gender", "level"]
    ]

    # insert user records
    for i, row in user_df.iterrows():
        cur.execute(user_table_insert, row)

    # insert songplay records
    for index, row in df.iterrows():
        
        # get songid and artistid from song and artist tables
        cur.execute(song_select, (row.song, row.artist, row.length))
        results = cur.fetchone()
        
        if results:
            songid, artistid = results
        else:
            songid, artistid = None, None

        # insert songplay record
        songplay_data = (row.start_time, row.userId, row.level, songid, artistid, row.sessionId, row.location, row.userAgent)
        cur.execute(songplay_table_insert, songplay_data)


def process_data(cur, conn, filepath, func):
    """
        Takes a root file paths and processes all files to be stored in the SQL database using the handler funct
    """
    
    # get all files matching extension from directory
    all_files = []
    for root, dirs, files in os.walk(filepath):
        files = glob.glob(os.path.join(root,'*.json'))
        for f in files :
            all_files.append(os.path.abspath(f))

    # get total number of files found
    num_files = len(all_files)
    print('{} files found in {}'.format(num_files, filepath))

    # iterate over files and process
    for i, datafile in enumerate(all_files, 1):
        func(cur, datafile)
        conn.commit()
        print('{}/{} files processed.'.format(i, num_files))


def main():
    """
        Main function that is called when ran as a script. It constructs the SQL cursors and calls the file processing 
        functions.
    """
    
    conn = psycopg2.connect("host=127.0.0.1 dbname=sparkifydb user=student password=student")
    cur = conn.cursor()

    process_data(cur, conn, filepath='data/song_data', func=process_song_file)
    process_data(cur, conn, filepath='data/log_data', func=process_log_file)

    conn.close()


if __name__ == "__main__":
    main()