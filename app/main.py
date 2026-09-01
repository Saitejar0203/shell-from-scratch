import sys


def main():
      #TODO: Uncomment the code below to pass the first stage
      sys.stdout.write("$ ")
      # Captures the user's command in the "command" variable
      command = input()
      # Prints the "<command>: command not found" message
      print(f"{command}: command not found")
      pass


if __name__ == "__main__":
    main()
