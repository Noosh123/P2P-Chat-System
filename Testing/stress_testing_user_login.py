import db 
import threading,time
import datetime 
import matplotlib.pyplot as plt

# demo


db = db.DB()
x=[]
y=[]
for i in range(2,500):
        
    threads = []
    for _ in range(i):
        t=threading.Thread(target=db.user_login,args=("bb","192.168.1.1", "9999", "1234"))
        threads.append(t)
    start_time = time.time()
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    # End time
    end_time = time.time()
    elapsed_time_millis = (end_time - start_time) * 1000
    print(f"Elapsed time for {i} threads: {elapsed_time_millis:.2f} milliseconds")
    x.append(i)
    y.append(elapsed_time_millis)
plt.semilogx(x,y)
plt.xlabel('Number of Threads')
plt.ylabel('Time (ms)')
plt.title('Stress Testing - User Login')
plt.savefig("Stress Testing - User Login")
plt.show() 

