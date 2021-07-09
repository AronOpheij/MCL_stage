from mcl_stage.mcl_stage import MCLMicroDrive
from pynput.keyboard import Listener, Key, KeyCode       # pip install pynput

class StageKeyboard:
    def __init__(self, stage):
        print('Esc to quit, arrow keys to move around, +- to change stepsize')
        self.stage = stage
        self.stepsizes = (
            ("0.1 u", .0001),
            ("1 u", .001),
            ("10 u", 0.01),     # float means mm
            ("100 u", 0.1),
            ("1 mm", 1.0),
        )
        self.stepsizeN = 2
        self.stepname, self.step = self.stepsizes[self.stepsizeN]

        def on_press(key):
            if hasattr(key, 'char'):
                if key.char == '+':
                    self.increase()
                if key.char == '-':
                    self.decrease()
                if key.char == 'p':
                    print("{:07.4f}, {:07.4f}".format(self.stage.xPos, self.stage.yPos))
            else:
                if key == Key.up:
                    self.take_step(2, 1)
                elif key == Key.down:
                    self.take_step(2, -1)
                elif key == Key.right:
                    self.take_step(1, 1)
                elif key == Key.left:
                    self.take_step(1, -1)


        def on_release(key):
            if key == Key.esc:
                # Stop listener
                return False

        with Listener(on_press=on_press, on_release=on_release) as listener:  # Setup the listener
            listener.join()  # Join the thread to the main thread


    def increase(self):
        self.stepsizeN = min(self.stepsizeN + 1, len(self.stepsizes) - 1)
        self._update_step()

    def decrease(self):
        self.stepsizeN = max(self.stepsizeN - 1, 0)
        self._update_step()

    def _update_step(self):
        self.stepname, self.step = self.stepsizes[self.stepsizeN]
        print('stepsize: '+self.stepname)

    def take_step(self, axis, dir):
        if self.step < .00101:
            self.stage._stepA(axis, int(self.step * 10000) * dir)
        # if type(self.step) is int:
        #     self.stage._stepA(axis, self.step * dir)
        else:
            self.stage._relA(axis, self.step * dir)




if __name__ == '__main__':

    dll_dir = r'E:\Action-Potential\Equipments\MCL_Python_Matlab'

    # stage = MCLMicroDrive(dll_dir)  # To look for the dll in a specific directory
    stage = MCLMicroDrive()         # To look for the dll in the directory where this file lives
    #stage = DummyMCLMicroDrive()    # To test with Dummy version

    # Start the keyboard control for the stage
    stage_keyboard = StageKeyboard(stage)
