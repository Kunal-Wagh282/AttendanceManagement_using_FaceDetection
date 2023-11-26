import cv2
import os
import tkinter as tk
from tkinter import simpledialog, messagebox, filedialog
from PIL import Image, ImageTk
import face_recognition
import mysql.connector
from datetime import datetime, timedelta
import numpy as np
import sys
import time
import subprocess



class CameraApp():
    def __init__(self, root):
        self.db = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            port=3306,
            database="attendance_db"
        )
        self.cursor = self.db.cursor()

        # Dictionary to keep track of recognized persons and their in-time
        self.recognized_persons = {}
        self.last_face_time = {}
        self.known_faces = self.get_known_faces()
        self.entry()
        self.first_value=self.f_value()
        self.CONSISTENCY_THRESHOLD = 5

        # Initialize variables for name consistency
        self.current_name = None
        self.consistent_name_start_time = None
        
        self.root = root

        self.root.title("Camera App")
        self.vid = cv2.VideoCapture(0)
        self.width, self.height = 800, 600
        self.vid.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.vid.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.create_layout()
        self.open_camera()
        
        
    def create_layout(self):
        # Create main frame
        main_frame = tk.Frame(self.root, padx=20, pady=20)
        main_frame.pack(expand=True, fill='both')
        
        # Left section for displaying name
        name_frame = tk.Frame(main_frame)
        name_frame.pack(side='left', padx=10)
        
        self.first_name_label = tk.Label(name_frame, text="First Name: ")
        self.first_name_label.pack(anchor='w', padx=10, pady=(10, 0))

        self.first_name_entry = tk.Entry(name_frame)
        self.first_name_entry.pack(anchor='w', padx=10, pady=(0, 10))
        
        self.last_name_label = tk.Label(name_frame, text="Last Name: ")
        self.last_name_label.pack(anchor='w', padx=10, pady=(10, 0))
        
        self.last_name_entry = tk.Entry(name_frame)
        self.last_name_entry.pack(anchor='w', padx=10, pady=(0, 10))
        
        self.course_label = tk.Label(name_frame, text="Course: ")
        self.course_label.pack(anchor='w', padx=10, pady=(10, 0))
        
        self.course_entry = tk.Entry(name_frame)
        self.course_entry.pack(anchor='w', padx=10, pady=(0, 10))

        self.in_time_label = tk.Label(name_frame, text="In Time: ")
        self.in_time_label.pack(anchor='w', padx=10, pady=(10, 0))
        
        self.in_time_entry = tk.Entry(name_frame)
        self.in_time_entry.pack(anchor='w', padx=10, pady=(0, 10))

        self.out_time_label = tk.Label(name_frame, text="Out Time: ")
        self.out_time_label.pack(anchor='w', padx=10, pady=(10, 0))
        
        self.out_time_entry = tk.Entry(name_frame)
        self.out_time_entry.pack(anchor='w', padx=10, pady=(0, 10))
        
        # Right section for camera display
        camera_frame = tk.Frame(main_frame, borderwidth=2, relief="solid")
        camera_frame.pack(side='right', padx=10, pady=10)
        
        self.label = tk.Label(camera_frame)
        self.label.pack()
        
        # Bottom section for buttons
        button_frame = tk.Frame(self.root)
        button_frame.pack(side='bottom', pady=10)
        
        self.admin_button = tk.Button(button_frame, text="Admin Login", command=self.admin_login)
        self.admin_button.pack(side='left', padx=10)

        self.Recalibrate_button = tk.Button(button_frame, text="Recalibrate", command=self.recalibrate)
        self.Recalibrate_button.pack(side='left', padx=10)
        
        # Add future buttons here
        
        self.root.bind('<Escape>', lambda e: self.root.quit())

    
        
        
    def open_camera(self):
        self.ret, self.frame = self.vid.read()
        if self.ret:
            self.in_time_entry.delete(0,'end')
            self.out_time_entry.delete(0,'end')
            self.first_name_entry.delete(0,'end')
            self.last_name_entry.delete(0,'end')
            self.course_entry.delete(0,'end')
            opencv_image = cv2.cvtColor(self.frame, cv2.COLOR_BGR2RGBA)
            captured_image = Image.fromarray(opencv_image)
            photo_image = ImageTk.PhotoImage(image=captured_image)
            self.label.photo_image = photo_image
            self.label.configure(image=photo_image)
            current_datetime = datetime.now().date()
            two_day = timedelta(days=2)
            yesterday = current_datetime - two_day 
            if(yesterday==self.first_value):
                self.reset() 
                self.first_value=self.f_value()    
            # Find face locations and encodings
            face_locations = face_recognition.face_locations(self.frame)
            face_encodings = face_recognition.face_encodings(self.frame, face_locations)
            if len(face_encodings) == 0:
                self.current_name = None
                self.consistent_name_start_time = None

            for face_encoding in face_encodings:
                matches = face_recognition.compare_faces(list(self.known_faces.values()), face_encoding,tolerance=0.6)
                self.mname = "Unknown Unknown"

                face_distances = face_recognition.face_distance(list(self.known_faces.values()), face_encoding)
                best_match_index = int(np.argmin(face_distances))

                if matches[best_match_index]:
                    
                    self.mname = list(self.known_faces.keys())[best_match_index]

                if self.mname != "Unknown Unknown":
                    if self.current_name != self.mname:
                        self.current_name = self.mname
                        self.consistent_name_start_time = datetime.now().time()
                    else:
                        # Check if name has been consistent for self.CONSISTENCY_THRESHOLD seconds
                        elapsed_time = datetime.combine(datetime.min.date(), datetime.now().time()) - datetime.combine(datetime.min.date(), self.consistent_name_start_time)
                        if elapsed_time >= timedelta(seconds=self.CONSISTENCY_THRESHOLD):
                            self.handle_attendance(self.mname)
                            self.current_name = None  # Reset self.current_name to avoid duplicate registrations
                
                fname,lname = self.mname.split(' ')
                if self.mname in self.recognized_persons:
                    self.in_time_entry.delete(0,'end')
                    self.in_time_entry.insert(0,str(self.recognized_persons[self.mname]).split(' ')[1])
                else:
                    self.in_time_entry.delete(0,'end')
                    self.in_time_entry.insert(0,'N/A')
                # Display recognized person's name and in-time/out-time on the frame 
                if self.mname in self.last_face_time:
                    
                    self.out_time_entry.delete(0,'end')
                    self.out_time_entry.insert(0,str(self.last_face_time[self.mname]).split(' ')[1])
                else:
                    self.out_time_entry.delete(0,'end')
                    self.out_time_entry.insert(0,'N/A')
                if self.mname != "Unknown Unknown":
                    self.cursor.execute("SELECT id, course FROM faces WHERE person_name = %s", (self.mname,))
                    result = self.cursor.fetchall()
                    # id = result[0][0]
                    course = result[0][1]
                else:
                    course='N/A'
                
                self.first_name_entry.delete(0,'end')   
                self.first_name_entry.insert(0,fname)

                self.last_name_entry.delete(0,'end')
                self.last_name_entry.insert(0,lname)

                self.course_entry.delete(0,'end')
                self.course_entry.insert(0,course)
            self.root.after(5, self.open_camera)


    def get_known_faces(self):
        self.cursor.execute("SELECT person_name, face_encoding FROM faces")
        
        result = self.cursor.fetchall()
        known_faces = {}

        for row in result:
            name = row[0]
            face_encoding_str = row[1]
            face_encoding = [float(val) for val in face_encoding_str.split(',')]
            known_faces[name] = face_encoding
            print(name)

        return known_faces
    
    def recalibrate(self):
        self.known_faces = self.get_known_faces()
        print("Recalibrated:", len(self.known_faces))
    # def recalibrate(self):
    #     self.root.destroy()
    #     time.sleep(2)
    #     python = sys.executable
    #     subprocess.call([python] + sys.argv)
    #     sys.exit()
    #     # self.known_faces = self.get_known_faces()
    #     # print("RE")
    #     # print(len(self.known_faces))
        
    def restart_program(self):
        self.root.destroy()
        python = sys.executable
        subprocess.call([python] + sys.argv)
        sys.exit()


    def reset(self):
        current_datetime = datetime.now().date()
        two_day = timedelta(days=1)
        yesterday = current_datetime - two_day
        select_query = "delete FROM attendance2 WHERE date=%s and out_time is null"
        self.cursor.execute(select_query, (yesterday,))
        self.db.commit()
        self.recognized_persons.clear()
        self.last_face_time.clear()
        print("Entry deleted")


    def handle_attendance(self,person_name):
        current_time = datetime.now()
        if person_name not in self.recognized_persons:
            self.recognized_persons[person_name] = current_time
            self.update_in_time(person_name)    
            print(f"{person_name}: In-time recorded.") 
        elif (current_time - self.recognized_persons.get(person_name, current_time)) > timedelta(minutes=0.09):
            #self.last_face_time[person_name] = current_time
            self.update_out_time(person_name)
            print(f"{person_name}: Out-time recorded.")


    # Update in-time for the recognized person
    def update_in_time(self,name):
        
        date=datetime.now().date()
        time=datetime.now().time()
        self.cursor.execute("SELECT id, course FROM faces WHERE person_name = %s", (name,))
        result = self.cursor.fetchall()
        id = result[0][0]
        course = result[0][1]

        query = "INSERT INTO attendance (id, name,course, in_time,date) VALUES (%s,%s,%s,%s,%s)"
        values = (id,name,course,time,date)
        self.cursor.execute(query, values)
        self.db.commit()
    # Update out-time for the recognized person
    def update_out_time(self,name):
        self.last_face_time[name] = datetime.now()
        time=datetime.now().time()
        query = "UPDATE attendance SET out_time = %s WHERE name = %s AND out_time IS NULL"
        values = (time,name)
        self.cursor.execute(query, values)
        self.db.commit()

    def f_value(self):
        #fetch first value of recognized_person dictionary 
        current_datetime = datetime.now()
        one_day = timedelta(days=1)
        first_value = (current_datetime - one_day).date()

        return first_value
    def entry(self):
        now_date = datetime.now().date()
        select_query = "SELECT name,in_time FROM attendance WHERE date=%s"
        self.cursor.execute(select_query, (now_date,))
        selected_rows = self.cursor.fetchall()
        for row in selected_rows:
            name, time_delta = row
            out_datetime = datetime.combine(now_date, datetime.min.time()) + time_delta
            self.recognized_persons[name] = out_datetime
        # Dictionary to keep track of the last time a person showed their face
        select_query = "SELECT name,out_time FROM attendance WHERE date=%s and out_time"
        self.cursor.execute(select_query, (now_date,))
        selected_rows = self.cursor.fetchall()
        for row in selected_rows:
            name, time_delta = row
            if time_delta==None:
                continue
            out_datetime = datetime.combine(now_date, datetime.min.time()) + time_delta
            self.last_face_time[name] = out_datetime

    def admin_login(self):
        password = simpledialog.askstring("Admin Login", "Enter password:", show='*')
        if password == "1234":
            print("Admin login successful")
            # Add your admin-specific functionality here
            self.root.iconify()  # Minimize the camera app window
            self.run_image_uploader_app()
        else:
            print("Incorrect password")
            messagebox.showerror("Error", "Incorrect password")
            
    
    def run_image_uploader_app(self):
        uploader_root = tk.Toplevel()  # Create a Toplevel window
        uploader_root.title("Image Uploader")
        app = ImageUploaderApp(uploader_root, self)
        app.run()

    def run(self):
        self.root.mainloop()
        
        # Release the video capture object
        cv2.destroyAllWindows()

        # Close the database connection when done
        self.cursor.close()
        self.db.close()
        self.vid.release()

class ImageUploaderApp(CameraApp):
    def __init__(self, root, camera_app):
        self.root = root
        self.camera_app = camera_app  # Reference to the CameraApp instance
        
        self.root.geometry("600x400")  # Set width and height
        self.root.protocol("WM_DELETE_WINDOW", self.back_to_camera_app)  # Handle window close event
        
        self.create_widgets()
        
    def create_widgets(self):
        self.first_name_label = tk.Label(self.root, text="First Name:")
        self.first_name_label.pack()
        
        self.first_name_entry = tk.Entry(self.root)
        self.first_name_entry.pack()
        
        self.last_name_label = tk.Label(self.root, text="Last Name:")
        self.last_name_label.pack()
        
        self.last_name_entry = tk.Entry(self.root)
        self.last_name_entry.pack()
        
        self.course_label = tk.Label(self.root, text="Course:")
        self.course_label.pack()
        
        self.course_entry = tk.Entry(self.root)
        self.course_entry.pack()
        
        self.browse_button = tk.Button(self.root, text="Browse Image", command=self.browse_image)
        self.browse_button.pack()
        
        self.submit_button = tk.Button(self.root, text="Submit", command=self.submit)
        self.submit_button.pack()
        
        self.status_label = tk.Label(self.root, text="")
        self.status_label.pack()

        self.back_button = tk.Button(self.root, text="Back", command=self.back_to_camera_app)
        self.back_button.pack()

        self.Recalibrate_button = tk.Button(self.root, text="Recalibrate", command=self.recalibrate)
        self.Recalibrate_button.pack(side='left', padx=10)
    def back_to_camera_app(self):

        self.root.destroy()  # Close the image uploader window
        self.camera_app.root.deiconify()  # Restore the camera app window
    def browse_image(self):
        file_path = filedialog.askopenfilename()
        self.file_path = file_path
    def submit(self):
        db = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        port=3306,
        database="attendance_db")
        cursor = db.cursor()
        first_name = self.first_name_entry.get()
        last_name = self.last_name_entry.get()
        course = self.course_entry.get()
        full_name = f"{first_name}_{last_name}_{course}"
        if hasattr(self, 'file_path'):
            image = Image.open(self.file_path)
            save_path = os.path.join("newimages", f"{full_name}.jpg")
            image.save(save_path)
            image =  face_recognition.load_image_file(save_path)
            face_encoding = face_recognition.face_encodings(image)[0]
            # Convert the face encoding to a string for storage in the database
            face_encoding_str = ",".join(str(val) for val in face_encoding)
            # Store the face encoding in the database
            insert_query = "INSERT INTO faces (person_name, course , face_encoding) VALUES (%s, %s, %s)"
            insert_values = (first_name+' '+last_name, course, face_encoding_str)
            cursor.execute(insert_query, insert_values)

            cursor.execute("SELECT LAST_INSERT_ID()")
            last_inserted_id = cursor.fetchone()[0]
            def convertToBinaryData(filename):
    # Convert digital data to binary format
                with open(filename, 'rb') as file:
                    binaryData = file.read()
                return binaryData


            def insertBLOB(emp_id, photo):
                
                connection = None  # Initialize the connection variable
                try:
                    connection = mysql.connector.connect(host='localhost',
                                                        user='root',
                                                        password='',
                                                        database='attendance_db')
                    cursor = connection.cursor()
                    sql_insert_blob_query = """INSERT INTO images (id, image) VALUES (%s, %s)"""
                    empPicture = convertToBinaryData(photo)
                    insert_blob_tuple = (emp_id, empPicture)
                    cursor.execute(sql_insert_blob_query, insert_blob_tuple)
                    connection.commit()
                    #print("Image inserted successfully as a BLOB into images table")
                except mysql.connector.Error as error:
                    print("Failed inserting BLOB data into MySQL table: {}".format(error))
                finally:
                    if connection is not None and connection.is_connected():
                        cursor.close()
                        connection.close()
                        
            insertBLOB(last_inserted_id,save_path)
            db.commit()
            self.status_label.config(text=f"Record saved successfully")
        cursor.close()
        db.close()
    def recalibrate(self):
        self.known_faces=CameraApp.known_faces
        self.known_faces = self.get_known_faces()
        print("Recalibrated:", len(self.known_faces))
    def run(self):
        self.root.mainloop()
if __name__ == "__main__":
    root = tk.Tk()
    app = CameraApp(root)
    app.run()