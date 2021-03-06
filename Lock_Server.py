################################# Imported Packages #############################################

from threading import Lock
import place_holder
from File_Server import TcpServer


#################################################################################################

class LockServer(TcpServer):
    messages = {place_holder.REQUEST_LOCK, place_holder.REQUEST_UNLOCK, place_holder.REQUEST_USE}
    locks_mutex = Lock()
    locks = {}

    # override request processing function
    def process_req(self, conn, request, vars):
        file_id = vars[0]
        client = vars[1]

        # lock request
        if request == place_holder.REQUEST_LOCK:
            try:
                # acquire locks mutex
                self.locks_mutex.acquire()
                # return failure if file is locked and lock owner is different client
                if file_id in self.locks and self.locks[file_id] != client:
                    self.send_msg(conn, place_holder.FAILURE.format("File locked by another client"))
                # otherwise okay to lock file for client and return success
                else:
                    self.locks[file_id] = client
                    self.send_msg(conn, place_holder.SUCCESS.format("Locked"))
            finally:
                self.locks_mutex.release()

        # unlock request
        elif request == place_holder.REQUEST_UNLOCK:
            try:
                # acquire locks mutex
                self.locks_mutex.acquire()
                # unlock and return success if file is locked and owned by client
                if file_id in self.locks and self.locks[file_id] == client:
                    del self.locks[file_id]
                    self.send_msg(conn, place_holder.SUCCESS.format("Unlocked"))
                # otherwise return failure if file not in array
                elif file_id not in self.locks:
                    self.send_msg(conn, place_holder.FAILURE.format("File not locked"))
                # otherwise return file locked by another client
                else:
                    self.send_msg(conn, place_holder.FAILURE.format("File locked by another client"))

            finally:
                self.locks_mutex.release()

        # usage request
        elif request == place_holder.REQUEST_USE:
            try:
                # acquire locks mutex
                self.locks_mutex.acquire()
                # return disallowed only if file is locked and owned by different client
                if file_id in self.locks and self.locks[file_id] != client:
                    self.send_msg(conn, place_holder.FAILURE.format("Disallowed"))
                # otherwise return allowed to access file
                else:
                    self.send_msg(conn, place_holder.SUCCESS.format("Allowed"))
            finally:
                self.locks_mutex.release()


if __name__ == "__main__":
    print "Lock Server started on " + str(place_holder.LOCK_SERVER)
    server = LockServer(place_holder.LOCK_SERVER)
