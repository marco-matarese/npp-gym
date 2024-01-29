from PyQt5 import QtWidgets
import time

from PyQt5 import QtCore
from PyQt5 import QtWidgets
from PyQt5.QtCore import QObject, QThread, pyqtSignal, QMutex
from PyQt5.QtCore import QRect, QPoint, Qt
from PyQt5.QtGui import QFont
from PyQt5.QtGui import QPainter
from PyQt5.QtWidgets import QLabel, QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QGridLayout, QFrame, QMessageBox
from PyQt5.QtWidgets import QStyle, QStyleOptionSlider

from model import NPPModel

# ACTIONS' CODES
SKIP = 0
SET_SAFETY_RODS_UP = 1
SET_SAFETY_RODS_DOWN = 2
SET_SUSTAIN_RODS_UP = 3
SET_SUSTAIN_RODS_MEDIUM = 4
SET_SUSTAIN_RODS_DOWN = 5
SET_FUEL_RODS_UP = 6
SET_FUEL_RODS_DOWN = 7
SET_REGULATORY_RODS_UP = 8
SET_REGULATORY_RODS_MEDIUM = 9
SET_REGULATORY_RODS_DOWN = 10
ADD_WATER_STEAM_GENERATOR = 11

COUNTDOWN_MAX = 20.0
countdown = COUNTDOWN_MAX
mutex = QMutex()


class LabeledSlider(QtWidgets.QWidget):
    def __init__(self, minimum, maximum, interval=1, orientation=Qt.Horizontal,
            labels=None, parent=None):
        super(LabeledSlider, self).__init__(parent=parent)

        levels=range(minimum, maximum+interval, interval)
        if labels is not None:
            if not isinstance(labels, (tuple, list)):
                raise Exception("<labels> is a list or tuple.")
            if len(labels) != len(levels):
                raise Exception("Size of <labels> doesn't match levels.")
            self.levels=list(zip(levels,labels))
        else:
            self.levels=list(zip(levels,map(str,levels)))

        if orientation==Qt.Horizontal:
            self.layout=QtWidgets.QVBoxLayout(self)
        elif orientation==Qt.Vertical:
            self.layout=QtWidgets.QHBoxLayout(self)
        else:
            raise Exception("<orientation> wrong.")

        # gives some space to print labels
        self.left_margin=10
        self.top_margin=10
        self.right_margin=10
        self.bottom_margin=10

        self.layout.setContentsMargins(self.left_margin,self.top_margin,
                self.right_margin,self.bottom_margin)

        self.sl=QtWidgets.QSlider(orientation, self)
        self.sl.setMinimum(minimum)
        self.sl.setMaximum(maximum)
        self.sl.setValue(minimum)
        if orientation==Qt.Horizontal:
            self.sl.setTickPosition(QtWidgets.QSlider.TicksBelow)
            self.sl.setMinimumWidth(300) # just to make it easier to read
        else:
            self.sl.setTickPosition(QtWidgets.QSlider.TicksLeft)
            self.sl.setMinimumHeight(300) # just to make it easier to read
        self.sl.setTickInterval(interval)
        self.sl.setSingleStep(1)

        self.layout.addWidget(self.sl)

    def setValue(self, v):
        if (self.sl.maximum() - self.sl.minimum()) <= 1:
            if v == 1:
                v = 0
            elif v == 0:
                v = 1
        else:
            if v == 0:
                v = 2
            elif v == 2:
                v = 0
        self.sl.setValue(v)

    def getValue(self):
        value = self.sl.value()
        if (self.sl.maximum() - self.sl.minimum()) <= 1:
            if value == 1:
                value = 0
            elif value == 0:
                value = 1
        else:
            if value == 0:
                value = 2
            elif value == 2:
                value = 0
        return value

    def paintEvent(self, e):

        super(LabeledSlider,self).paintEvent(e)

        style=self.sl.style()
        painter=QPainter(self)
        st_slider=QStyleOptionSlider()
        st_slider.initFrom(self.sl)
        st_slider.orientation=self.sl.orientation()

        length=style.pixelMetric(QStyle.PM_SliderLength, st_slider, self.sl)
        available=style.pixelMetric(QStyle.PM_SliderSpaceAvailable, st_slider, self.sl)

        self.sl.setStyleSheet("border: 0px solid black;")

        for v, v_str in self.levels:

            # get the size of the label
            rect=painter.drawText(QRect(), Qt.TextDontPrint, v_str)

            if self.sl.orientation()==Qt.Horizontal:
                # I assume the offset is half the length of slider, therefore
                # + length//2
                x_loc=QStyle.sliderPositionFromValue(self.sl.minimum(),
                        self.sl.maximum(), v, available)+length//2

                # left bound of the text = center - half of text width + L_margin
                left=x_loc-rect.width()//2+self.left_margin
                bottom=self.rect().bottom()

                # enlarge margins if clipping
                if v==self.sl.minimum():
                    if left<=0:
                        self.left_margin=rect.width()//2-x_loc
                    if self.bottom_margin<=rect.height():
                        self.bottom_margin=rect.height()

                    self.layout.setContentsMargins(self.left_margin,
                            self.top_margin, self.right_margin,
                            self.bottom_margin)

                if v==self.sl.maximum() and rect.width()//2>=self.right_margin:
                    self.right_margin=rect.width()//2
                    self.layout.setContentsMargins(self.left_margin,
                            self.top_margin, self.right_margin,
                            self.bottom_margin)

            else:
                y_loc=QStyle.sliderPositionFromValue(self.sl.minimum(),
                        self.sl.maximum(), v, available, upsideDown=True)

                bottom=y_loc+length//2+rect.height()//2+self.top_margin-3
                # there is a 3 px offset that I can't attribute to any metric

                left=self.left_margin-rect.width()
                if left<=0:
                    self.left_margin=rect.width()+2
                    self.layout.setContentsMargins(self.left_margin,
                            self.top_margin, self.right_margin,
                            self.bottom_margin)

            pos=QPoint(left, bottom)
            painter.drawText(pos, v_str)

        return
    

class NPPGui(QWidget):

    def __init__(self, window, control, condition, exp_type, user_id):
        super(NPPGui, self).__init__()

        self.user_id = user_id

        self.control = control
        self.condition = condition
        self.exp_type = exp_type

        self.indicated_action = None
        self.action_declaration = None
        self.main_layout = QVBoxLayout()
        self.sub_layout_1 = QHBoxLayout()
        self.frame_1 = QFrame()
        self.frame_1.setLayout(self.sub_layout_1)

        self.fuel_rods_pos = 1
        self.safety_rods_pos = 1
        self.regulatory_rods_pos = 0
        self.sustain_rods_pos = 0

        self.sub_layout_2 = QHBoxLayout()
        self.sub_layout_2_1 = QGridLayout()
        self.temp_layout = QVBoxLayout()
        self.temperature_label = QLabel("Temperatura dell'acqua nel nocciolo")
        self.temperature_label.setStyleSheet("border: 0px solid black;")
        self.temperature_box = QLabel('80.0 °C')
        self.temperature_box.setStyleSheet("border: 0px solid black;")
        self.temp_layout.addWidget(self.temperature_label)
        self.temp_layout.addWidget(self.temperature_box)
        self.temp_frame = QFrame()
        self.temp_frame.setLayout(self.temp_layout)
        self.temp_frame.setStyleSheet("border: 1px solid black; background-color: rgb(220,220,220);")
        self.temp_frame.setFixedSize(320, 70)
        self.sub_layout_2_1.addWidget(self.temp_frame, 0, 0, alignment=Qt.AlignLeft)
        self.pressure_layout = QVBoxLayout()
        self.pressure_label = QLabel("Pressione del nocciolo")
        self.pressure_label.setStyleSheet("border: 0px solid black;")
        self.pressure_box = QLabel('30.0 ATM')
        self.pressure_box.setStyleSheet("border: 0px solid black;")
        self.pressure_layout.addWidget(self.pressure_label)
        self.pressure_layout.addWidget(self.pressure_box)
        self.pressure_frame = QFrame()
        self.pressure_frame.setLayout(self.pressure_layout)
        self.pressure_frame.setStyleSheet("border: 1px solid black; background-color: rgb(220,220,220);")
        self.pressure_frame.setFixedSize(180, 70)
        self.sub_layout_2_1.addWidget(self.pressure_frame, 0, 1, alignment=Qt.AlignLeft)
        self.water_label = QLabel("Livello dell'acqua nel generatore di vapore")
        self.water_label.setStyleSheet("border: 0px solid black;")
        self.water_box = QLabel('120 m2')
        self.water_box.setStyleSheet("border: 0px solid black;")
        self.water_layout = QVBoxLayout()
        self.water_layout.addWidget(self.water_label)
        self.water_layout.addWidget(self.water_box)
        self.water_frame = QFrame()
        self.water_frame.setLayout(self.water_layout)
        self.water_frame.setFixedSize(320, 70)
        self.water_frame.setStyleSheet("border: 1px solid black; background-color: rgb(220,220,220);")
        self.sub_layout_2_1.addWidget(self.water_frame, 1, 0, alignment=Qt.AlignLeft)
        self.power_label = QLabel("Potenza del reattore")
        self.power_label.setStyleSheet("border: 0px solid black;")
        self.power_box = QLabel('0.0 MW')
        self.power_box.setStyleSheet("border: 0px solid black;")
        self.power_layout = QVBoxLayout()
        self.power_layout.addWidget(self.power_label)
        self.power_layout.addWidget(self.power_box)
        self.power_frame = QFrame()
        self.power_frame.setLayout(self.power_layout)
        self.power_frame.setStyleSheet("border: 1px solid black; background-color: rgb(220,220,220);")
        self.power_frame.setFixedSize(180, 70)
        self.sub_layout_2_1.addWidget(self.power_frame, 1, 1, alignment=Qt.AlignLeft)
        self.energy_label = QLabel("Energia prodotta nello scorso step")
        self.energy_box = QLabel('0.0 MWh')
        self.energy_layout = QVBoxLayout()
        self.energy_layout.addWidget(self.energy_label)
        self.energy_layout.addWidget(self.energy_box)
        self.energy_frame = QFrame()
        self.energy_frame.setLayout(self.energy_layout)
        self.energy_frame.setStyleSheet("border: 1px solid black; background-color: rgb(220,220,220);")
        self.energy_frame.setFixedSize(320, 70)
        self.sub_layout_2_1.addWidget(self.energy_frame, 2, 0, alignment=Qt.AlignLeft)

        self.energy_tot_label = QLabel("Energia totale prodotta")
        self.energy_tot_box = QLabel('0.0 MWh')
        self.energy_tot_box.setStyleSheet("border: 0px solid black;")
        self.energy_tot_label.setStyleSheet("border: 0px solid black;")
        self.energy_tot_layout = QVBoxLayout()
        self.energy_tot_layout.addWidget(self.energy_tot_label)
        self.energy_tot_layout.addWidget(self.energy_tot_box)
        self.energy_tot_frame = QFrame()
        self.energy_tot_frame.setLayout(self.energy_tot_layout)
        self.energy_tot_frame.setStyleSheet("border: 1px solid black; background-color: rgb(220,220,220);")
        self.energy_tot_frame.setFixedSize(180, 70)
        self.sub_layout_2_1.addWidget(self.energy_tot_frame, 2, 1, alignment=Qt.AlignLeft)

        self.energy_label.setStyleSheet("border: 0px solid black;")
        self.energy_box.setStyleSheet("border: 0px solid black;")

        self.sub_layout_2_1.setSpacing(20)
        self.sub_layout_1.addLayout(self.sub_layout_2_1)

        self.sub_layout_1.setSpacing(50)

        self.sub_layout_2 = QGridLayout()
        self.frame_2 = QFrame()
        self.frame_2.setLayout(self.sub_layout_2)
        self.safety_label = QLabel("Barre di sicurezza")
        self.safety_label.setStyleSheet("border: 0px solid black;")
        self.sustain_label = QLabel("Barre di sostegno")
        self.sustain_label.setStyleSheet("border: 0px solid black;")
        self.fuel_label = QLabel("Barre di combustibile")
        self.fuel_label.setStyleSheet("border: 0px solid black;")
        self.regulatory_label = QLabel("Barre di regolamento")
        self.regulatory_label.setStyleSheet("border: 0px solid black;")
        self.sub_layout_2.addWidget(self.safety_label, 0, 0, alignment=Qt.AlignCenter)
        self.sub_layout_2.addWidget(self.sustain_label, 0, 1, alignment=Qt.AlignCenter)
        self.sub_layout_2.addWidget(self.fuel_label, 0, 2, alignment=Qt.AlignCenter)
        self.sub_layout_2.addWidget(self.regulatory_label, 0, 3, alignment=Qt.AlignCenter)

        self.safety_slider = LabeledSlider(minimum=0, maximum=1, interval=1, orientation=Qt.Vertical, labels=['DENTRO', 'FUORI'])
        self.safety_slider.setValue(self.safety_rods_pos)
        self.sustain_slider = LabeledSlider(minimum=0, maximum=2, interval=1, orientation=Qt.Vertical, labels=['DENTRO', 'MEDIO', 'FUORI'])
        self.sustain_slider.setValue(self.sustain_rods_pos)
        self.fuel_slider = LabeledSlider(minimum=0, maximum=1, interval=1, orientation=Qt.Vertical, labels=['DENTRO', 'FUORI'])
        self.fuel_slider.setValue(self.fuel_rods_pos)
        self.regulatory_slider = LabeledSlider(minimum=0, maximum=2, interval=1, orientation=Qt.Vertical, labels=['DENTRO', 'MEDIO', 'FUORI'])
        self.regulatory_slider.setValue(self.regulatory_rods_pos)
        self.sub_layout_2.addWidget(self.safety_slider, 1, 0, alignment=Qt.AlignCenter)
        self.sub_layout_2.addWidget(self.sustain_slider, 1, 1, alignment=Qt.AlignCenter)
        self.sub_layout_2.addWidget(self.fuel_slider, 1, 2, alignment=Qt.AlignCenter)
        self.sub_layout_2.addWidget(self.regulatory_slider, 1, 3, alignment=Qt.AlignCenter)

        self.water_button = QPushButton("AGGIUNGI ACQUA\nNEL GENERATORE\nDI VAPORE")
        self.def_button_stylesheet = self.water_button.styleSheet()
        self.water_button.setStyleSheet("QPushButton {background-color: rgb(211,211,211); border:1px solid rgb(255, 170, 255); "
                                   "border-radius: 4px;}"
                                   "QPushButton:hover {background-color: rgb(220,220,220); border:1px solid rgb(255, 170, 255);}"
                                   "QPushButton:pressed {background-color: rgb(178, 190, 181); border:1px solid rgb(255, 170, 255);}")
        self.water_button.setFixedSize(200, 100)
        self.water_button.setFont(QFont('Arial', 15))

        self.sub_layout_2.addWidget(self.water_button, 1, 5, alignment=Qt.AlignBottom)
        self.sub_layout_2.setSpacing(20)

        self.sub_layout_3 = QHBoxLayout()
        self.ask_icub_button = QPushButton("CHIEDI\nCOSA")
        self.ask_icub_button.setFont(QFont('Arial', 15))
        self.ask_icub_button.setFixedSize(80, 80)
        self.ask_icub_button.setStyleSheet("QPushButton {background-color: rgb(211,211,211); border:1px solid rgb(255, 170, 255); "
                                      "border-radius: 4px;}"
                                      "QPushButton:hover {background-color: rgb(220,220,220); border:1px solid rgb(255, 170, 255);}"
                                      "QPushButton:pressed {background-color: rgb(178, 190, 181); border:1px solid rgb(255, 170, 255);}")
        self.ask_icub_button.setEnabled(False)
        self.ask_why_button = QPushButton("CHIEDI\nPERCHÈ")
        self.ask_why_button.setFont(QFont('Arial', 15))
        self.ask_why_button.setFixedSize(100, 80)
        self.ask_why_button.setStyleSheet("QPushButton {background-color: rgb(211,211,211); border:1px solid rgb(255, 170, 255); "
                                     "border-radius: 4px;}"
                                     "QPushButton:hover {background-color: rgb(220,220,220); border:1px solid rgb(255, 170, 255);}"
                                     "QPushButton:pressed {background-color: rgb(178, 190, 181); border:1px solid rgb(255, 170, 255);}")
        self.ask_why_button.setEnabled(False)
        self.skip_button = QPushButton('SKIP')
        self.skip_button.setFont(QFont('Arial', 15))
        self.skip_button.setFixedSize(80, 80)
        self.skip_button.setStyleSheet("QPushButton {background-color: rgb(211,211,211); border:1px solid rgb(255, 170, 255); "
                                  "border-radius: 4px;}"
                                  "QPushButton:hover {background-color: rgb(220,220,220); border:1px solid rgb(255, 170, 255);}"
                                  "QPushButton:pressed {background-color: rgb(178, 190, 181); border:1px solid rgb(255, 170, 255);}")
        self.sub_layout_2.addWidget(self.skip_button, 1, 4, alignment=Qt.AlignBottom)
        self.confirm_button = QPushButton('CONFERMA')
        self.confirm_button.setFont(QFont('Arial', 15))
        self.confirm_button.setFixedSize(140, 80)
        self.confirm_button.setStyleSheet("QPushButton {background-color: rgb(211,211,211); border:1px solid rgb(255, 170, 255); "
                                     "border-radius: 4px;}"
                                     "QPushButton:hover {background-color: rgb(220,220,220); border:1px solid rgb(255, 170, 255);}"
                                     "QPushButton:pressed {background-color: rgb(178, 190, 181); border:1px solid rgb(255, 170, 255);}")
        self.sub_layout_3.addWidget(self.ask_icub_button, alignment=Qt.AlignLeft)
        self.sub_layout_3.addWidget(self.ask_why_button, alignment=Qt.AlignLeft)
        # self.sub_layout_3.addWidget(self.skip_button, alignment=Qt.AlignRight)
        self.sub_layout_3.addWidget(self.confirm_button, alignment=Qt.AlignRight)
        self.sub_layout_3.setSpacing(10)
        self.frame_3 = QFrame()
        self.frame_3.setLayout(self.sub_layout_3)

        self.main_layout.addWidget(self.frame_1)
        self.frame_1.setStyleSheet("border: 0px solid black;")
        self.main_layout.addWidget(self.frame_2)
        self.frame_2.setStyleSheet("border: 1px solid black; background-color: rgb(192,192,192);")
        self.main_layout.addWidget(self.frame_3)
        self.main_layout.setSpacing(100)

        self.central_widget = QWidget()
        self.central_widget.setLayout(self.main_layout)
        window.setCentralWidget(self.central_widget)

        self.error_msgbox = QMessageBox()
        self.error_msgbox.setWindowTitle("Rilevata anomalia!")
        self.error_msgbox.setIcon(QMessageBox.Critical)

        self.action_error_msgbox = QMessageBox()
        self.action_error_msgbox.setWindowTitle("Errore")
        self.action_error_msgbox.setIcon(QMessageBox.Warning)
        self.action_error_msgbox.setText("Devi specificare un'azione prima di cliccare su 'Conferma'.")

        self.confirm_button.clicked.connect(self.confirm_button_clicked)
        self.water_button.clicked.connect(self.water_button_clicked)
        self.skip_button.clicked.connect(self.skip_button_clicked)
        self.ask_icub_button.clicked.connect(self.ask_icub_button_clicked)
        self.ask_why_button.clicked.connect(self.ask_why_button_clicked)
        self.fuel_slider.sl.valueChanged.connect(self.fuel_slider_value_changed)
        self.safety_slider.sl.valueChanged.connect(self.safety_slider_value_changed)
        self.sustain_slider.sl.valueChanged.connect(self.sustain_slider_value_changed)
        self.regulatory_slider.sl.valueChanged.connect(self.regulatory_slider_value_changed)

        self.npp_thread = QThread()
        self.npp_obj = NPPModel(user_id, exp_type)

        QtCore.QMetaObject.connectSlotsByName(window)

    def show_countdown_error_msg(self):
        # if their value changed without confirming...
        self.regulatory_slider.setValue(self.regulatory_rods_pos)
        self.safety_slider.setValue(self.safety_rods_pos)
        self.sustain_slider.setValue(self.sustain_rods_pos)
        self.fuel_slider.setValue(self.fuel_rods_pos)
        self.water_button.setEnabled(True)
        self.ask_why_button.setEnabled(False)
        self.ask_icub_button.setEnabled(True)

        self.do_action_routine(SKIP)

    def do_action_routine(self, action_code):
        """
        Ask the model to perform tha action; set the features' labels;
        if an anomaly has been detected, show the error message and restart the values.
        """
        icub_action_phrase = self.npp_obj.get_DT_action()
        obs, anomaly, info = self.npp_obj.perform_user_action(action_code)
        self.npp_obj.comm_partner_model_obs(obs)
        self.set_features_labels(obs, info['energy'])

        self.control.log_on_data_dumper(["OBSERVATION", str(obs)])
        self.control.log_on_data_dumper(["NOT ASKED ICUB ACTION", icub_action_phrase])
        self.control.log_on_data_dumper(["ENERGY", str(info['energy'])])
        if anomaly:
            self.control.anomaly_detected(info['info_anomalies'])

            self.show_error_msgbox(info['info_anomalies'])

            # restart features values in both the env and gui
            self.npp_obj.restart()
            new_obs = self.npp_obj.get_observation()
            self.set_features_labels(new_obs)
            self.fuel_rods_pos = 1
            self.safety_rods_pos = 1
            self.regulatory_rods_pos = 0
            self.sustain_rods_pos = 0
            self.fuel_slider.setValue(self.fuel_rods_pos)
            self.safety_slider.setValue(self.safety_rods_pos)
            self.regulatory_slider.setValue(self.regulatory_rods_pos)
            self.sustain_slider.setValue(self.sustain_rods_pos)

    def set_features_labels(self, obs, energy=None):
        self.temperature_box.setText("{:.1f}".format(obs[0]) + ' °C')
        self.pressure_box.setText("{:.1f}".format(obs[1]) + ' ATM')
        self.water_box.setText("{:.1f}".format(obs[2]) + ' m3')
        self.power_box.setText("{:.1f}".format(obs[3]) + ' MW')

        if energy is not None:
            self.energy_box.setText("{:.1f}".format(energy) + ' MWh')
            energy_tot_text = self.energy_tot_box.text()
            tot_energy = float(energy_tot_text[:-4])
            tot_energy += float(energy)
            self.energy_tot_box.setText("{:.1f}".format(tot_energy) + ' MWh')

    def start_npp_thread(self):
        self.npp_obj.moveToThread(self.npp_thread)
        self.npp_thread.start()

    def set_indicated_action(self, gui_element):
        self.indicated_action = gui_element

    def show_error_msgbox(self, msg):
        self.error_msgbox.setText(msg)
        self.error_msgbox.exec()

    def confirm_button_clicked(self):
        if self.indicated_action is None or self.indicated_action == self.ask_icub_button or self.indicated_action == self.ask_why_button:
            self.action_error_msgbox.exec()

        else:

            command = ""
            confirmed_action = None
            do_action_routine = False

            if self.indicated_action == self.water_button:
                self.water_button.setEnabled(True)
                # self.do_action_routine(ADD_WATER_STEAM_GENERATOR)
                confirmed_action = ADD_WATER_STEAM_GENERATOR
                do_action_routine = True
                command = "ADD WATER STEAM GENERATOR"
                
            elif self.indicated_action == self.skip_button:
                self.skip_button.setEnabled(True)

                confirmed_action = SKIP
                do_action_routine = True
                command = "SKIP"

            elif self.indicated_action == self.fuel_slider:
                self.fuel_rods_pos = self.fuel_slider.getValue()
                if self.fuel_rods_pos == 0:

                    confirmed_action = SET_FUEL_RODS_UP
                    do_action_routine = True
                    command = "FUEL RODS UP"
                else:

                    confirmed_action = SET_FUEL_RODS_DOWN
                    do_action_routine = True
                    command = "FUEL RODS DOWN"

            elif self.indicated_action == self.regulatory_slider:
                self.regulatory_rods_pos = self.regulatory_slider.getValue()

                if self.regulatory_rods_pos == 0:

                    confirmed_action = SET_REGULATORY_RODS_UP
                    do_action_routine = True
                    command = "REGULATORY RODS UP"
                elif self.regulatory_rods_pos == 1:

                    confirmed_action = SET_REGULATORY_RODS_MEDIUM
                    do_action_routine = True
                    command = "REGULATORY RODS MEDIUM"
                else:

                    confirmed_action = SET_REGULATORY_RODS_DOWN
                    do_action_routine = True
                    command = "REGULATORY RODS DOWN"

            elif self.indicated_action == self.safety_slider:
                self.safety_rods_pos = self.safety_slider.getValue()
                if self.safety_rods_pos == 0:

                    confirmed_action = SET_SAFETY_RODS_UP
                    do_action_routine = True
                    command = "SAFETY RODS UP"
                else:

                    confirmed_action = SET_SAFETY_RODS_DOWN
                    do_action_routine = True
                    command = "SAFETY RIDS DOWN"

            elif self.indicated_action == self.sustain_slider:
                self.sustain_rods_pos = self.sustain_slider.getValue()

                if self.sustain_rods_pos == 0:

                    confirmed_action = SET_SUSTAIN_RODS_UP
                    do_action_routine = True
                    command = "SUSTAIN RODS UP"
                elif self.sustain_rods_pos == 1:

                    confirmed_action = SET_SUSTAIN_RODS_MEDIUM
                    do_action_routine = True
                    command = "SUSTAIN RODS MEDIUM"
                else:

                    confirmed_action = SET_SUSTAIN_RODS_DOWN
                    do_action_routine = True
                    command = "SUSTAIN RODS DOWN"

            if do_action_routine:
                self.do_action_routine(confirmed_action)
                self.npp_obj.comm_partner_model_confirmed_action(confirmed_action)

            self.control.log_on_data_dumper(["CONFIRMED ACTION", command])
            self.indicated_action = None

        if self.ask_why_button.isEnabled():
            self.ask_why_button.setEnabled(False)

        self.ask_icub_button.setEnabled(False)

    def skip_button_clicked(self):
        self.control.log_on_data_dumper(["GUI INTERACTION", "SKIP BUTTON"])

        # if their value changed without confirming...
        self.regulatory_slider.setValue(self.regulatory_rods_pos)
        self.safety_slider.setValue(self.safety_rods_pos)
        self.sustain_slider.setValue(self.sustain_rods_pos)
        self.fuel_slider.setValue(self.fuel_rods_pos)

        self.action_declaration = SKIP

        self.set_indicated_action(self.skip_button)
        self.skip_button.setEnabled(False)
        self.water_button.setEnabled(True)
        if self.exp_type == 'training':
            self.ask_icub_button.setEnabled(True)

    def water_button_clicked(self):
        self.control.log_on_data_dumper(["GUI INTERACTION", "WATER BUTTON"])

        # if their value changed without confirming...
        self.regulatory_slider.setValue(self.regulatory_rods_pos)
        self.safety_slider.setValue(self.safety_rods_pos)
        self.sustain_slider.setValue(self.sustain_rods_pos)
        self.fuel_slider.setValue(self.fuel_rods_pos)

        self.action_declaration = ADD_WATER_STEAM_GENERATOR

        self.set_indicated_action(self.water_button)
        self.water_button.setEnabled(False)
        self.skip_button.setEnabled(True)
        if self.exp_type == 'training':
            self.ask_icub_button.setEnabled(True)

    def ask_icub_button_clicked(self):
        self.control.log_on_data_dumper(["GUI INTERACTION", "ASK WHAT BUTTON"])

        action_phrase = self.npp_obj.get_DT_action()
        self.control.user_asked_what(action_phrase)

        self.npp_obj.comm_partner_model_action_declaration(self.action_declaration)

        self.ask_why_button.setEnabled(True)
        self.ask_icub_button.setEnabled(False)

    def ask_why_button_clicked(self):
        self.control.log_on_data_dumper(["GUI INTERACTION", "ASK WHY BUTTON"])

        if self.condition == 'classical':
            explanation = self.npp_obj.get_classical_explanation()
        else:
            explanation = self.npp_obj.get_useraware_explanation(user_indicated_action=self.action_declaration)
        self.control.user_asked_why(explanation)

        self.ask_icub_button.setEnabled(False)
        self.ask_why_button.setEnabled(False)

    def fuel_slider_value_changed(self):
        curr_fuel_value = self.fuel_slider.getValue()

        if curr_fuel_value != self.fuel_rods_pos:
            self.control.log_on_data_dumper(["GUI INTERACTION", "FUEL SLIDER"], curr_fuel_value)

            curr_fuel_rods_pos = self.fuel_slider.getValue()
            if self.fuel_rods_pos == 0:
                self.action_declaration = SET_FUEL_RODS_UP
            else:
                self.action_declaration = SET_FUEL_RODS_DOWN

            self.set_indicated_action(self.fuel_slider)
        else:
            self.set_indicated_action(None)

        # if their value changed without confirming...
        self.regulatory_slider.setValue(self.regulatory_rods_pos)
        self.safety_slider.setValue(self.safety_rods_pos)
        self.sustain_slider.setValue(self.sustain_rods_pos)

        if self.exp_type == 'training':
            self.ask_icub_button.setEnabled(True)

        self.skip_button.setEnabled(True)
        self.water_button.setEnabled(True)

    def regulatory_slider_value_changed(self):
        curr_regulatory_value = self.regulatory_slider.getValue()

        if curr_regulatory_value != self.regulatory_rods_pos:
            self.control.log_on_data_dumper(["GUI INTERACTION", "REGULATORY SLIDER"], curr_regulatory_value)
            self.set_indicated_action(self.regulatory_slider)

            if self.regulatory_rods_pos == 0:
                self.action_declaration = SET_REGULATORY_RODS_UP
            elif self.regulatory_rods_pos == 1:
                self.action_declaration = SET_REGULATORY_RODS_MEDIUM
            else:
                self.action_declaration = SET_REGULATORY_RODS_DOWN
        else:
            self.set_indicated_action(None)

        # if their value changed without confirming...
        self.fuel_slider.setValue(self.fuel_rods_pos)
        self.safety_slider.setValue(self.safety_rods_pos)
        self.sustain_slider.setValue(self.sustain_rods_pos)

        if self.exp_type == 'training':
            self.ask_icub_button.setEnabled(True)

        self.skip_button.setEnabled(True)
        self.water_button.setEnabled(True)

    def safety_slider_value_changed(self):
        curr_safety_value = self.safety_slider.getValue()

        if curr_safety_value != self.safety_rods_pos:
            self.control.log_on_data_dumper(["GUI INTERACTION", "SAFETY SLIDER"], curr_safety_value)
            self.set_indicated_action(self.safety_slider)

            if self.safety_rods_pos == 0:
                self.action_declaration = SET_SAFETY_RODS_UP
            else:
                self.action_declaration = SET_SAFETY_RODS_DOWN
        else:
            self.set_indicated_action(None)

        # if their value changed without confirming...
        self.fuel_slider.setValue(self.fuel_rods_pos)
        self.regulatory_slider.setValue(self.regulatory_rods_pos)
        self.sustain_slider.setValue(self.sustain_rods_pos)

        if self.exp_type == 'training':
            self.ask_icub_button.setEnabled(True)

        self.skip_button.setEnabled(True)
        self.water_button.setEnabled(True)

    def sustain_slider_value_changed(self):
        curr_sustain_value = self.sustain_slider.getValue()

        if curr_sustain_value != self.sustain_rods_pos:
            self.control.log_on_data_dumper(["GUI INTERACTION", "SUSTAIN SLIDER"], curr_sustain_value)
            self.set_indicated_action(self.sustain_slider)

            if self.sustain_rods_pos == 0:
                self.action_declaration = SET_SUSTAIN_RODS_UP
            elif self.sustain_rods_pos == 1:
                self.action_declaration = SET_SUSTAIN_RODS_MEDIUM
            else:
                self.action_declaration = SET_SUSTAIN_RODS_DOWN
        else:
            self.set_indicated_action(None)

        # if their value changed without confirming...
        self.fuel_slider.setValue(self.fuel_rods_pos)
        self.regulatory_slider.setValue(self.regulatory_rods_pos)
        self.safety_slider.setValue(self.safety_rods_pos)

        # self.ask_why_button.setEnabled(False)
        if self.exp_type == 'training':
            self.ask_icub_button.setEnabled(True)
        self.skip_button.setEnabled(True)
        self.water_button.setEnabled(True)
