################################# Imported Packages #############################################

import os
import sys
from threading import Thread
import place_holder
from File_Server import TcpServer


#################################################################################################

class ReplicationSlave(Thread):
    def __init__(self, port):
        print "Replication Slave " + str(port) + " Created!"
        Thread.__init__(self)
        self.port = port
        self.daemon = True
        self.start()

    def run(self):
        ReplicationServer(self.port)


class ReplicationServer(TcpServer):
    messages = {place_holder.READ_FILE, place_holder.WRITE_FILE, place_holder.DELETE_FILE, place_holder.SUCCESS,
                place_holder.FAILURE}
    slaves = []
    files = {}

    # override init function to import slaves list
    def __init__(self, port, slaves=[]):
        self.slaves = slaves
        self.is_slave = True if slaves == [] else False
        if not os.path.exists(str(port)):
            os.makedirs(str(port))
        TcpServer.__init__(self, port)

    # override request processing function
    def process_req(self, conn, request, vars):
        # requesting file data from replication server
        if request == place_holder.READ_FILE or request == place_holder.WRITE_FILE or request == place_holder.DELETE_FILE:
            file_id = vars[0]
            client = vars[1]

            # update file data if requesting file update
            if request == place_holder.WRITE_FILE:
                data = vars[2]

                # check with lock server for permission
                if not self.is_slave:
                    (resp, resp_vars) = self.propagate_msg(place_holder.REQUEST_USE, (file_id, client),
                                                           place_holder.LOCK_SERVER)

                # write file to all servers if usage is allowed
                if self.is_slave or resp == place_holder.SUCCESS:
                    self.files[file_id] = True

                    # write file to disk
                    f = open(os.path.join(str(self.port), file_id), 'w')
                    f.write(data)
                    f.close()

                    # propagate request to all slaves if master
                    for slave in self.slaves:
                        print "PROPAGATING WRITE REQUEST TO " + str(slave)
                        self.propagate_msg(request, vars, slave, False)
                    # respond to client with success message
                    if not self.is_slave:
                        self.send_msg(conn, place_holder.SUCCESS.format("File written successfully."))
                else:
                    self.send_msg(conn, resp.format(*resp_vars))

            else:
                # check if file exists for read and delete
                if file_id in self.files:

                    # check with lock server for permission
                    if not self.is_slave:
                        (resp, resp_vars) = self.propagate_msg(place_holder.REQUEST_USE, (file_id, client),
                                                               place_holder.LOCK_SERVER)

                    if self.is_slave or resp == place_holder.SUCCESS:
                        # send back file data if requesting data
                        if request == place_holder.READ_FILE:
                            f = open(os.path.join(str(self.port), file_id), 'r')
                            self.send_msg(conn, place_holder.RETURN_FILE_DATA.format(f.read()))
                            f.close()

                        # delete file from index if requesting file deletion
                        elif request == place_holder.DELETE_FILE:
                            del self.files[file_id]

                            # propagate request to all slaves
                            for slave in self.slaves:
                                print "PROPAGATING DELETE REQUEST TO  " + str(slave)
                                self.propagate_msg(request, vars, slave, False)
                            # respond to client with success message
                            if not self.is_slave:
                                self.send_msg(conn, place_holder.SUCCESS.format("File deleted successfully."))
                    else:
                        self.send_msg(conn, resp.format(*resp_vars))

                # else return file not found
                else:
                    self.error(conn, "File not found.")


if __name__ == "__main__":
    if len(sys.argv) != 2 or not sys.argv[1].isdigit():
        sys.exit("Port number required")
    print "Replication Master started on " + sys.argv[1]

    slaves = []

    # initialise multiple other slave servers
    for i in range(place_holder.REP_SERVER_COPIES):
        port = int(sys.argv[1]) + (i + 1)
        slaves.append(port)
        ReplicationSlave(port)

    # initialise master replication server
    master = ReplicationServer(int(sys.argv[1]), slaves)
