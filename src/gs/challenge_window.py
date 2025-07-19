import sys
import asyncio
from PySide6.QtWidgets import (QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
                               QTableWidget, QTableWidgetItem, QCheckBox, QLabel,
                               QComboBox, QPushButton, QFrame, QTextEdit, QSplitter,
                               QApplication, QHeaderView)
from PySide6.QtCore import Qt, QTimer, QObject, Signal, Slot
import aiohttp
from datetime import datetime, timedelta
from qasync import QEventLoop, asyncSlot


class GurushotChallenge:
    def __init__(self, id, title, end_time, votes):
        self.id = id
        self.title = title
        self.end_time = end_time
        self.votes = votes
        self.selected_strategy = "Normal"
        self.status = "Not Started"


class AsyncFetcher(QObject):
    finished = Signal(list)

    def __init__(self):
        super().__init__()

    async def fetch_challenges(self):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get('https://api.gurushots.com/rest_mobile/get_challenges') as response:
                    data = await response.json()
                    challenges = []
                    for challenge_data in data.get('challenges', []):
                        challenge = GurushotChallenge(
                            id=challenge_data['id'],
                            title=challenge_data['title'],
                            end_time=datetime.fromtimestamp(challenge_data['end_time']),
                            votes=challenge_data.get('votes', 0)
                        )
                        challenges.append(challenge)
                    self.finished.emit(challenges)
        except Exception as e:
            print(f"Error fetching challenges: {e}")
            self.finished.emit([])


class ChallengeWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gurushot Challenges")
        self.setGeometry(100, 100, 800, 600)

        self.challenges = []
        self.selected_challenges = set()
        self.profiles = ["Profile 1", "Profile 2", "Profile 3"]

        #self.fetcher = AsyncFetcher()
        #self.fetcher.finished.connect(self.on_challenges_fetched)

        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        # Top bar with refresh button and profile selector
        top_bar = QHBoxLayout()

        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.refresh_challenges)
        top_bar.addWidget(refresh_button)

        top_bar.addStretch()

        profile_label = QLabel("Profile:")
        top_bar.addWidget(profile_label)

        self.profile_combo = QComboBox()
        self.profile_combo.addItems(self.profiles)
        self.profile_combo.currentTextChanged.connect(self.change_profile)
        top_bar.addWidget(self.profile_combo)

        main_layout.addLayout(top_bar)

        # Separator line
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(line)

        # Splitter for challenge table and result panel
        splitter = QSplitter(Qt.Vertical)
        main_layout.addWidget(splitter)

        # Challenge table
        self.challenge_table = QTableWidget()
        self.challenge_table.setColumnCount(7)
        self.challenge_table.setHorizontalHeaderLabels(
            ["Select", "Title", "End Time", "Remaining", "Votes", "Status", "Strategy"])
        self.challenge_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        splitter.addWidget(self.challenge_table)

        # Result panel
        self.result_panel = QTextEdit()
        self.result_panel.setReadOnly(True)
        splitter.addWidget(self.result_panel)

        # Set initial sizes for splitter
        splitter.setSizes([400, 200])

        # Bottom buttons
        button_layout = QHBoxLayout()
        fill_button = QPushButton("FILL")
        fin_button = QPushButton("FIN")
        in_progress_button = QPushButton("En cours")
        fill_button.clicked.connect(self.fill_selected_challenges)
        fin_button.clicked.connect(self.finish_selected_challenges)
        in_progress_button.clicked.connect(self.show_in_progress_challenges)
        button_layout.addWidget(fill_button)
        button_layout.addWidget(fin_button)
        button_layout.addWidget(in_progress_button)
        main_layout.addLayout(button_layout)

        # Timer pour mettre à jour l'affichage toutes les secondes
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_challenge_list)
        self.timer.start(5000)

        # Start fetching challenges
        asyncio.ensure_future(self.fetch_challenges())

    @asyncSlot()
    async def fetch_challenges(self):
        self.result_panel.append("Fetching challenges...")
        await self.fetcher.fetch_challenges()

    @Slot(list)
    def on_challenges_fetched(self, challenges):
        self.challenges = self.sort_challenges(challenges)
        self.populate_challenge_table()
        self.result_panel.append("Challenges fetched successfully!")

    def sort_challenges(self, challenges):
        return sorted(challenges, key=lambda x: x.end_time)

    def populate_challenge_table(self):
        self.challenge_table.setRowCount(len(self.challenges))
        self.challenge_table.
        for row, challenge in enumerate(self.challenges):
            # Select checkbox
            checkbox = QCheckBox()
            checkbox.setChecked(challenge.id in self.selected_challenges)
            checkbox.stateChanged.connect(lambda state, cid=challenge.id: self.toggle_challenge_selection(cid))
            self.challenge_table.setCellWidget(row, 0, checkbox)

            # Title
            self.challenge_table.setItem(row, 1, QTableWidgetItem(challenge.title))

            # End Time
            self.challenge_table.setItem(row, 2, QTableWidgetItem(challenge.end_time.strftime('%d/%m/%Y %HH:%MM')))

            # Remaining Time (will be updated by timer)
            remaining_label = QLabel()
            remaining_label.setObjectName(f"remaining_label_{challenge.id}")
            self.challenge_table.setCellWidget(row, 3, remaining_label)

            # Votes
            self.challenge_table.setItem(row, 4, QTableWidgetItem(str(challenge.votes)))

            # Status
            status_label = QLabel(challenge.status)
            status_label.setObjectName(f"status_label_{challenge.id}")
            self.challenge_table.setCellWidget(row, 5, status_label)

            # Strategy
            strategy_combo = QComboBox()
            strategy_combo.addItems(["Normal", "Aggressive", "Conservative"])
            strategy_combo.setCurrentText(challenge.selected_strategy)
            strategy_combo.currentTextChanged.connect(lambda text, c=challenge: self.update_challenge_strategy(c, text))
            self.challenge_table.setCellWidget(row, 6, strategy_combo)

        self.challenge_table.sortItems(2)

    def toggle_challenge_selection(self, challenge_id):
        if challenge_id in self.selected_challenges:
            self.selected_challenges.remove(challenge_id)
        else:
            self.selected_challenges.add(challenge_id)

    def update_challenge_strategy(self, challenge, strategy):
        challenge.selected_strategy = strategy

    def fill_selected_challenges(self):
        result = f"Filling challenges: {self.selected_challenges}\n"
        for challenge_id in self.selected_challenges:
            challenge = next((c for c in self.challenges if c.id == challenge_id), None)
            if challenge:
                challenge.status = "In Progress"
                result += f"Filled {challenge.title} with strategy {challenge.selected_strategy}\n"
                status_label = self.findChild(QLabel, f"status_label_{challenge.id}")
                if status_label:
                    status_label.setText(challenge.status)
        self.result_panel.append(result)

    def finish_selected_challenges(self):
        result = f"Finishing challenges: {self.selected_challenges}\n"
        for challenge_id in self.selected_challenges:
            challenge = next((c for c in self.challenges if c.id == challenge_id), None)
            if challenge:
                challenge.status = "Finished"
                result += f"Finished {challenge.title} with strategy {challenge.selected_strategy}\n"
                status_label = self.findChild(QLabel, f"status_label_{challenge.id}")
                if status_label:
                    status_label.setText(challenge.status)
        self.result_panel.append(result)

    def show_in_progress_challenges(self):
        in_progress_challenges = [c for c in self.challenges if c.status == "In Progress"]
        result = "Challenges en cours:\n"
        if in_progress_challenges:
            for challenge in in_progress_challenges:
                result += f"- {challenge.title} (Strategy: {challenge.selected_strategy})\n"
        else:
            result += "Aucun challenge en cours.\n"
        self.result_panel.append(result)

    def update_challenge_list(self):
        now = datetime.now()
        for challenge in self.challenges:
            remaining_time = challenge.end_time - now
            remaining_hours = int(remaining_time.total_seconds() / 3600)
            label = self.findChild(QLabel, f"remaining_label_{challenge.id}")
            if label:
                label.setText(f"{remaining_hours} hours")

    @asyncSlot()
    async def refresh_challenges(self):
        self.result_panel.append("Refreshing challenges...")
        await self.fetch_challenges()

    def change_profile(self, profile):
        self.result_panel.append(f"Changed to profile: {profile}")


def main():
    app = QApplication(sys.argv)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    window = ChallengeWindow()
    window.show()

    with loop:
        loop.run_forever()


if __name__ == "__main__":
    main()