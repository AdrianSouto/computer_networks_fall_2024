import socket
import sys
import re


class FTPClient:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.control_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.control_socket.connect((self.host, self.port))
        self.receive_response()  # Recibir mensaje de bienvenida

    def receive_response(self):
        response = self.control_socket.recv(4096).decode('utf-8')
        print(response, end='')
        return response

    def send_command(self, command):
        self.control_socket.send((command + '\r\n').encode('utf-8'))
        return self.receive_response()

    def login(self, username, password):
        user_response = self.send_command(f'USER {username}')
        pass_response = self.send_command(f'PASS {password}')
        return user_response, pass_response

    def pasv(self):
        response = self.send_command('PASV')
        if "227" in response:  # Respuesta de modo pasivo
            # Extraer la dirección IP y el puerto de la respuesta
            ip_port = re.search(r'\((\d+,\d+,\d+,\d+,\d+,\d+)\)', response).group(1)
            ip_parts = list(map(int, ip_port.split(',')))
            ip = '.'.join(map(str, ip_parts[:4]))
            port = (ip_parts[4] << 8) + ip_parts[5]
            return ip, port
        else:
            raise Exception("Error al entrar en modo PASV.")

    def list_files(self):
        ip, port = self.pasv()
        data_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        data_socket.connect((ip, port))
        list_response = self.send_command('LIST')
        data = data_socket.recv(4096).decode('utf-8')
        data_socket.close()
        print(data)
        return list_response, data

    def retr(self, filename):
        ip, port = self.pasv()
        data_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        data_socket.connect((ip, port))
        retr_response = self.send_command(f'RETR {filename}')
        with open(filename, 'wb') as file:
            while True:
                data = data_socket.recv(4096)
                if not data:
                    break
                file.write(data)
        data_socket.close()
        print(f"Archivo '{filename}' descargado correctamente.")
        return retr_response

    def print_working_directory(self):
        response = self.send_command('PWD')
        if "257" in response:  # Respuesta exitosa de PWD
            print(response)
            return response
        else:
            raise Exception("Error al obtener el directorio actual.")

    def change_working_directory(self, directory):
        response = self.send_command(f'CWD {directory}')
        if "250" in response:  # Respuesta exitosa de CWD
            print(f"Directorio cambiado a '{directory}'.")
            return response
        else:
            raise Exception(f"Error al cambiar al directorio '{directory}'.")

    def rename(self, from_name, to_name):
        rnfr_response = self.send_command(f'RNFR {from_name}')
        if "350" in rnfr_response:  # Respuesta exitosa de RNFR
            rnto_response = self.send_command(f'RNTO {to_name}')
            if "250" in rnto_response:  # Respuesta exitosa de RNTO
                print(f"Archivo renombrado de '{from_name}' a '{to_name}'.")
            else:
                raise Exception(f"Error al renombrar el archivo a '{to_name}'.")
        else:
            raise Exception(f"Error al renombrar el archivo desde '{from_name}'.")
        return rnfr_response, rnto_response

    def make_directory(self, directory):
        response = self.send_command(f'MKD {directory}')
        if "257" in response:  # Respuesta exitosa de MKD
            print(f"Directorio '{directory}' creado correctamente.")
        else:
            raise Exception(f"Error al crear el directorio '{directory}'.")
        return response

    def delete_file(self, filename):
        response = self.send_command(f'DELE {filename}')
        if "250" in response:  # Respuesta exitosa de DELE
            print(f"Archivo '{filename}' eliminado correctamente.")
        else:
            raise Exception(f"Error al eliminar el archivo '{filename}'.")
        return response

    def stor(self, local_filepath, remote_filename):
        ip, port = self.pasv()
        data_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        data_socket.connect((ip, port))
        stor_response = self.send_command(f'STOR {remote_filename}')
        with open(local_filepath, 'rb') as file:
            while True:
                data = file.read(4096)
                if not data:
                    break
                data_socket.sendall(data)
        data_socket.close()
        final_response = self.receive_response()
        if "226" in final_response or "250" in final_response:
            print(f"Archivo '{local_filepath}' subido como '{remote_filename}' correctamente.")
        else:
            raise Exception(f"Error al subir el archivo '{local_filepath}'.")
        return stor_response, final_response

    def remove_directory(self, directory):
        response = self.send_command(f'RMD {directory}')
        if "250" in response:  # Respuesta exitosa de RMD
            print(f"Directorio '{directory}' eliminado correctamente.")
        else:
            raise Exception(f"Error al eliminar el directorio '{directory}'.")
        return response

    def quit(self):
        response = self.send_command('QUIT')
        self.control_socket.close()
        print("Conexión cerrada.")
        return response

def manage_requests(client, command, arg1, arg2):
    try:
        if command == "LIST":
            list_response, data = client.list_files()
            print(list_response, data)
        elif command == "DELE":
            if not arg1:
                print("Falta el argumento requerido: -a para el comando DELE")
                return
            dele_response = client.delete_file(arg1)
            print(dele_response)
        elif command == "STOR":
            if not arg1 or not arg2:
                print("Faltan los argumentos requeridos: -a (archivo local) y -b (nombre remoto) para el comando STOR")
                return
            stor_response, final_response = client.stor(arg1, arg2)
            print(stor_response, final_response)

        elif command == "RETR":
            if not arg1:
                print("Falta el argumento requerido: -a para el comando RETR")
                return
            retr_response = client.retr(arg1)
            print(retr_response)
        elif command == "PWD":
            pwd_response = client.print_working_directory()
            print(pwd_response)
        elif command == "CWD":
            if not arg1:
                print("Falta el argumento requerido: -a para el comando CWD")
                return
            cwd_response = client.change_working_directory(arg1)
            print(cwd_response)
        elif command == "RNFR":
            if not arg1 or not arg2:
                print("Faltan los argumentos requeridos: -a y -b para el comando RNFR")
                return
            rnfr_response, rnto_response = client.rename(arg1, arg2)
            print(rnfr_response, rnto_response)
        elif command == "MKD":
            if not arg1:
                print("Falta el argumento requerido: -a para el comando MKD")
                return
            mkd_response = client.make_directory(arg1)
            print(mkd_response)
        elif command == "RMD":
            if not arg1:
                print("Falta el argumento requerido: -a para el comando RMD")
                return
            rmd_response = client.remove_directory(arg1)
            print(rmd_response)
        elif command:
            print(f"Comando '{command}' no reconocido.")
        else:
            print("No se proporcionó ningún comando.")
    except Exception as e:
        print(f"Error durante la ejecución del comando '{command}': {str(e)}")

    quit_response = client.quit()
    print(quit_response)

def main():
    cant_args = {
        "LIST": 0,
        "DELE": 1,
        "STOR": 2,
        "RETR": 1,
        "PWD": 0,
        "CWD": 1,
        "RNFR": 2,
        "MKD": 1,
        "RMD": 1
    }

    print("Bienvenido, para salir inserte 'exit'")
    host = input("Inserte el host: ")
    if host == "exit":
        return
    port = int(input("Inserte el puerto: "))
    if port == "exit":
        return
    user = input("Inserte el usuario: ")
    if user == "exit":
        return
    password = input("Inserte la contraseña: ")
    if password == "exit":
        return
    while True:
        command = input("Inserte un comando (DELE, LIST, STOR, RETR, PWD, CWD, RNFR, MKD, RMD): ")
        if command == "exit":
            break
        if command not in cant_args:
            print("Comando no reconocido")
            continue

        args = ["",""]
        for i in range(cant_args[command]):
            arg = input(f"Inserte el argumento {i+1}: ")
            if arg == "exit":
                break
            args[i] = arg

        client = FTPClient(host, port)
        user_response, pass_response = client.login(user, password)
        manage_requests(client, command, args[0], args[1])




if __name__ == "__main__":
    main()