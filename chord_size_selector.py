import pygame
import os
import importlib
from itertools import combinations
from edo_graphs2 import smallest_rotation

BLACK = (0, 0, 0)
DARKEST_GRAY = (20, 20, 20)
DARKER_GRAY = (25, 25, 25)
VERY_DARK_GRAY = (30, 30, 30)
DARK_GRAY = (50, 50, 50)
MEDIUM_DARK_GRAY = (60, 60, 60)
MEDIUM_GRAY = (70, 70, 70)
GRAY = (100, 100, 100)
LIGHT_GRAY = (170, 170, 170)
LIGHTER_GRAY = (190, 190, 190)
VERY_LIGHT_GRAY = (220, 220, 220)
LIGHTEST_GRAY = (210, 210, 210)
WHITE = (255, 255, 255)
BLUE = (0, 100, 255)
SELECTED_BG = (50, 50, 0)
SLIDER_COLOR = (230, 217, 217)

GENERATE_Y_OFFSET = 0


CHARACTERS = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
CHAR_TO_VALUE = {char: index for index, char in enumerate(CHARACTERS)}

def base62_to_int(b62_str):
    return sum(CHAR_TO_VALUE[char] * (62 ** i) for i, char in enumerate(reversed(b62_str)))

def generate_chord_sizes(edo):
    chord_sizes = [sorted({smallest_rotation(format(sum(1 << i for i in comb), f'0{edo}b'))[0][::-1] 
            for comb in combinations(range(edo), s)}, key=lambda x: int(x[::-1], 2)) 
            for s in range(edo+1)]
    chord_states1 = [[False for _ in chord_set] for chord_set in chord_sizes]
    chord_states2 = [[False for _ in chord_set] for chord_set in chord_sizes]
    return chord_sizes, chord_states1, chord_states2

class ChordSizeSelector:
    def __init__(self):
        pygame.init()
        self.setup_constants()
        self.setup_fonts()
        self.create_selector_panel()
        self.calculate_window_size()
        self.screen = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE)
        pygame.display.set_caption("edo graphs v0.2")
        self.create_regions()
        self.create_print_button()
        self.setup_state()
        self.generate_and_save_chord_sizes()
        self.load_chord_sizes()
        self.scroll_offset = 0
        self.max_scroll_offset = 0 
        self.old_button_index = 0
        self.draw()

    def setup_constants(self):
        self.margin, self.selector_height, self.region_height = 10, 20, 25
        self.min_button_width, self.top_margin, self.label_height = 13, 10, 20
        self.CHAR_WIDTH, self.BINARY_SQUARE_SIZE = 11, 15
        self.labels = ["edo", "shapes", "rotations", "interval variations",
                       "NOT shapes", "NOT rotations", "NOT interval variations"]
        self.slider_height = 8  # Height of the quantized slider

    def setup_fonts(self):
        font_path = os.path.join('assets', 'JetBrainsMono-Regular.otf')
        self.font = pygame.font.Font(font_path, 18)
        self.label_font = pygame.font.Font(font_path, 14)
        self.selector_font = pygame.font.Font(font_path, 14)
        self.print_button_font = pygame.font.Font(font_path, 15)

    def setup_state(self):
        self.dragging = False
        self.drag_start = self.drag_end = self.active_region = self.mouse_down_pos = None
        self.symbols = self.chord_sizes = self.chord_states1 = self.chord_states2 = []
        self.pending_edo_update = None
        self.slider_positions = {1: None, 4: None}
        self.dragging_slider = None

    def create_selector_panel(self):
        self.selector_panel = {"buttons": list(CHARACTERS[:len(CHARACTERS)//3]), "rects": [], "selected": 12}

    def calculate_window_size(self):
        edo = base62_to_int(self.selector_panel["buttons"][self.selector_panel["selected"]])
        self.left_region_width = edo * self.BINARY_SQUARE_SIZE
        selector_width = len(self.selector_panel["buttons"]) * self.CHAR_WIDTH
        toggleable_width = (self.selector_panel["selected"] + 1) * self.min_button_width
        self.width = max(self.left_region_width + selector_width,
                         self.left_region_width + toggleable_width,
                         self.left_region_width + 200)
        self.height = 7 * (self.region_height + self.label_height) + 8 * self.margin + 25
        self.update_selector_rects()

    def create_top_bar(self, x, y, width, height, label):
        return {
            "buttons": self.selector_panel["buttons"],
            "rects": self.selector_panel["rects"],
            "rect": pygame.Rect(x, y + self.label_height, width, height),
            "label": label,
            "is_top_bar": True
        }

    def create_regions(self):
        self.regions = []
        region_width = (self.selector_panel["selected"] + 1) * self.min_button_width
        for i, label in enumerate(self.labels):
            x, y = self.left_region_width, i * (self.region_height + self.label_height + self.margin) + self.top_margin
            if i == 0:
                self.regions.append(self.create_top_bar(x, y, self.width - self.left_region_width, self.selector_height, label))
            else:
                adjusted_width = region_width - (0 if i in [1, 4] else self.min_button_width)
                adjusted_x = x
                region = self.create_region(adjusted_x, y, adjusted_width, self.region_height, label, i in [1, 4], i in [2, 5])
                if i in [1, 4]:
                    region["slider_rect"] = pygame.Rect(adjusted_x, y + self.label_height + self.region_height - 1, adjusted_width, self.slider_height)
                self.regions.append(region)

    def create_region(self, x, y, width, height, label, is_extended, is_rotations):
        buttons = []
        selected_index = self.selector_panel["selected"]
        # if label in ["interval variations", "NOT interval variations"]:
        button_labels = self.selector_panel["buttons"][:selected_index + (1 if is_extended else 0)]
        button_width = width // len(button_labels)
        for i, button_label in enumerate(button_labels):
            button_rect = pygame.Rect(x + i * button_width, y + self.label_height, button_width, height)
            buttons.append({"rect": button_rect, "label": button_label, "enabled": (is_rotations and (i < 1))})
        return {"buttons": buttons, "rect": pygame.Rect(x, y + self.label_height, width, height), "label": label, "is_top_bar": False}

    def create_print_button(self):
        print_text = self.print_button_font.render("generate", True, WHITE)
        print_rect = print_text.get_rect()
        print_rect.centerx = self.left_region_width + (self.width - self.left_region_width) // 2
        print_rect.bottom = self.height - GENERATE_Y_OFFSET
        self.print_button = {"rect": print_rect, "label": "generate"}

    def update_selector_rects(self):
        self.selector_panel["rects"] = [pygame.Rect(self.left_region_width + i * self.CHAR_WIDTH, self.top_margin + self.label_height, 
                                                   self.CHAR_WIDTH, self.selector_height) for i in range(len(self.selector_panel["buttons"]))]

    def draw(self):
        self.screen.fill(VERY_DARK_GRAY)
        pygame.draw.rect(self.screen, DARKEST_GRAY, pygame.Rect(0, 0, self.left_region_width, self.height))
        
        self.draw_persistent_binaries()

        for region in self.regions:
            self.draw_region(region)

        pygame.draw.rect(self.screen, DARKER_GRAY, self.print_button["rect"])
        print_text = self.print_button_font.render(self.print_button["label"], True, LIGHTEST_GRAY)
        self.screen.blit(print_text, self.print_button["rect"].topleft)

        pygame.display.flip()

    def draw_persistent_binaries(self):
        edo = base62_to_int(self.regions[0]["buttons"][self.selector_panel["selected"]])
        for row in [1, 4]:
            if self.slider_positions[row] is not None:
                button_index = self.slider_positions[row]
                chord_states = self.chord_states1 if row == 1 else self.chord_states2
                self.draw_binaries(self.chord_sizes[button_index], chord_states[button_index], edo)
                return  # Only draw for the first active slider

        if self.symbols:
            self.draw_binaries(self.symbols, [False] * len(self.symbols), base62_to_int(self.regions[0]["buttons"][self.selector_panel["selected"]]))

    def draw_binaries(self, binaries, states, edo):
        visible_height = self.height
        total_height = len(binaries) * self.BINARY_SQUARE_SIZE
        self.max_scroll_offset = max(0, total_height - visible_height)
        
        surface = pygame.Surface((self.left_region_width, total_height))
        surface.fill(BLACK)
        
        for i, state in enumerate(states):
            if state:
                pygame.draw.rect(surface, SELECTED_BG, 
                                pygame.Rect(0, i * self.BINARY_SQUARE_SIZE, 
                                            self.left_region_width, self.BINARY_SQUARE_SIZE))
        for i in range(1,edo):
            pygame.draw.line(surface, MEDIUM_DARK_GRAY, (i * self.BINARY_SQUARE_SIZE, 0), 
                            (i * self.BINARY_SQUARE_SIZE, total_height))
        for i in range(1,len(binaries)):
            pygame.draw.line(surface, MEDIUM_DARK_GRAY, (0, i * self.BINARY_SQUARE_SIZE), 
                            (self.left_region_width, i * self.BINARY_SQUARE_SIZE))
        for i, (binary, state) in enumerate(zip(binaries, states)):
            for j, bit in enumerate(binary):
                if bit == '1':
                    color = BLUE if state else VERY_LIGHT_GRAY
                    pygame.draw.rect(surface, color, 
                                    pygame.Rect(j * self.BINARY_SQUARE_SIZE + 1, i * self.BINARY_SQUARE_SIZE + 1, 
                                                self.BINARY_SQUARE_SIZE - 1, self.BINARY_SQUARE_SIZE - 1))
        
        self.screen.blit(surface, (0, 0), (0, self.scroll_offset, self.left_region_width, visible_height))

    def handle_mouse_down(self, pos):
        self.mouse_down_pos = pos
        for i, rect in enumerate(self.selector_panel["rects"]):
            if rect.collidepoint(pos):
                self.pending_edo_update = i
                return

        for region in self.regions:
            if region["rect"].collidepoint(pos) and not region["is_top_bar"]:
                self.active_region = region
                self.initial_states = [button["enabled"] for button in region["buttons"]]
                break

            # Check if the click is on a slider
            if region["label"] in ["shapes", "NOT shapes"]:
                row = 1 if region["label"] == "shapes" else 4
                if region["slider_rect"].collidepoint(pos):
                    self.dragging_slider = row
                    self.handle_slider_drag(pos, row)
                elif self.slider_positions[row] is not None:
                    # Check if click is on a binary in the left region
                    edo = base62_to_int(self.regions[0]["buttons"][self.selector_panel["selected"]])
                    button_index = self.slider_positions[row]
                    binaries = self.chord_sizes[button_index]
                    chord_states = self.chord_states1 if row == 1 else self.chord_states2
                    for i, binary in enumerate(binaries):
                        binary_rect = pygame.Rect(0, i * self.BINARY_SQUARE_SIZE - self.scroll_offset, self.left_region_width, self.BINARY_SQUARE_SIZE)
                        if binary_rect.collidepoint(pos):
                            chord_states[button_index][i] = not chord_states[button_index][i]
                            self.save_chord_sizes()
                            self.draw()
                            return

    def generate_and_save_chord_sizes(self):
        edo = base62_to_int(self.regions[0]["buttons"][self.selector_panel["selected"]])
        self.chord_sizes, self.chord_states1, self.chord_states2 = generate_chord_sizes(edo)
        self.save_chord_sizes()
        self.load_chord_sizes()

    def save_chord_sizes(self):
        with open("chord_sizes.py", "w") as f:
            f.write("CHORD_SIZES = " + repr(self.chord_sizes) + "\n")
            f.write("CHORD_STATES1 = " + repr(self.chord_states1) + "\n")
            f.write("CHORD_STATES2 = " + repr(self.chord_states2) + "\n")

    def load_chord_sizes(self):
        try:
            import chord_sizes
            importlib.reload(chord_sizes)
            self.chord_sizes = chord_sizes.CHORD_SIZES
            self.chord_states1 = chord_sizes.CHORD_STATES1
            self.chord_states2 = chord_sizes.CHORD_STATES2
        except ImportError:
            print("Error: Could not load chord_sizes.py")
            self.chord_sizes = []
            self.chord_states1 = []
            self.chord_states2 = []

    def draw_region(self, region):
        label_surf = self.label_font.render(region["label"], True, LIGHT_GRAY)
        label_rect = label_surf.get_rect(topleft=(self.left_region_width, region["rect"].top - self.label_height))
        self.screen.blit(label_surf, label_rect)

        if region["is_top_bar"]:
            for j, (char, rect) in enumerate(zip(region["buttons"], region["rects"])):
                color = VERY_LIGHT_GRAY if j == self.selector_panel["selected"] else DARK_GRAY
                pygame.draw.rect(self.screen, color, rect)
                text_surf = self.selector_font.render(char, True, BLACK if j == self.selector_panel["selected"] else LIGHTER_GRAY)
                text_rect = text_surf.get_rect(center=(rect.centerx, rect.centery))
                self.screen.blit(text_surf, text_rect)
        else:
            for button in region["buttons"]:
                if self.dragging and self.active_region == region and self.is_in_drag_range(button["rect"].centerx):
                    bg_color = VERY_LIGHT_GRAY if not self.initial_states[region["buttons"].index(button)] else BLACK
                    text_color = BLACK if not self.initial_states[region["buttons"].index(button)] else WHITE
                else:
                    bg_color = VERY_LIGHT_GRAY if button["enabled"] else BLACK
                    text_color = BLACK if button["enabled"] else WHITE

                pygame.draw.rect(self.screen, bg_color, button["rect"])
                text_surf = self.font.render(button["label"], True, text_color)
                text_rect = text_surf.get_rect(center=button["rect"].center)
                self.screen.blit(text_surf, text_rect)

            if region["label"] in ["shapes", "NOT shapes"]:
                row = 1 if region["label"] == "shapes" else 4
                pygame.draw.rect(self.screen, GRAY, region["slider_rect"])
                
                chord_states = self.chord_states1 if row == 1 else self.chord_states2
                
                for i, button in enumerate(region["buttons"]):
                    chord_size = base62_to_int(button["label"])
                    any_chord_true = any(chord_states[chord_size]) if chord_size < len(chord_states) else False
                    
                    slider_x = region["slider_rect"].left + i * region["slider_rect"].width // len(region["buttons"])
                    slider_width = region["slider_rect"].width // len(region["buttons"])
                    slider_color = BLUE if any_chord_true else MEDIUM_GRAY
                    pygame.draw.rect(self.screen, slider_color, pygame.Rect(slider_x, region["slider_rect"].top, slider_width, region["slider_rect"].height))
                
                if self.slider_positions[row] is not None:
                    slider_x = region["slider_rect"].left + self.slider_positions[row] * region["slider_rect"].width // len(region["buttons"])
                    slider_width = region["slider_rect"].width // len(region["buttons"])
                    pygame.draw.rect(self.screen, SLIDER_COLOR, pygame.Rect(slider_x, region["slider_rect"].top, slider_width, region["slider_rect"].height))

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left mouse button
                    self.handle_mouse_down(event.pos)
                elif event.button == 4:  # Scroll up
                    self.scroll_offset = max(0, self.scroll_offset - 30)
                    self.draw()
                elif event.button == 5:  # Scroll down
                    self.scroll_offset = min(self.max_scroll_offset, self.scroll_offset + 30)
                    self.draw()
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self.handle_mouse_up(event.pos)
            elif event.type == pygame.MOUSEMOTION:
                if event.buttons[0]:
                    self.handle_mouse_drag(event.pos)
            elif event.type == pygame.VIDEORESIZE:
                self.handle_resize(event.size)

        if self.pending_edo_update is not None:
            self.symbols = []
            self.selector_panel["selected"] = self.pending_edo_update
            self.update_layout()
            self.generate_and_save_chord_sizes()
            self.pending_edo_update = None
            self.slider_positions = {1: None, 4: None}
            self.scroll_offset = 0
            self.draw()

        return True

    def handle_mouse_up(self, pos):
        if self.dragging and self.active_region:
            self.apply_drag_selection()
        elif self.mouse_down_pos == pos:
            self.handle_click(pos)

        self.reset_drag_state()
        self.draw()

    def handle_click(self, pos):
        if self.print_button["rect"].collidepoint(pos):
            self.print_all_enabled()
            return

        for region in self.regions:
            if region["rect"].collidepoint(pos):
                if not region["is_top_bar"]:
                    for button in region["buttons"]:
                        if button["rect"].collidepoint(pos):
                            button["enabled"] = not button["enabled"]
                            return

    def handle_mouse_drag(self, pos):
        if self.dragging_slider is not None:
            self.handle_slider_drag(pos, self.dragging_slider)
        elif not self.dragging and self.active_region:
            if abs(pos[0] - self.mouse_down_pos[0]) > 5 or abs(pos[1] - self.mouse_down_pos[1]) > 5:
                self.dragging = True
                self.drag_start = self.mouse_down_pos
        if self.dragging:
            self.drag_end = pos
        self.draw()

    def handle_slider_drag(self, pos, row):
        region = self.regions[row]
        relative_x = pos[0] - region["slider_rect"].left
        button_width = region["slider_rect"].width / len(region["buttons"])
        button_index = int(relative_x / button_width)
        if button_index != self.old_button_index:
            self.scroll_offset = 0
        self.old_button_index = button_index
        
        if 0 <= button_index < len(region["buttons"]):
            self.slider_positions[row] = button_index
        else:
            self.slider_positions[row] = None

    def handle_resize(self, size):
        self.width, self.height = size
        edo = base62_to_int(self.regions[0]["buttons"][self.selector_panel["selected"]])
        self.left_region_width = edo * self.BINARY_SQUARE_SIZE
        self.width = max(self.width, self.left_region_width + len(self.selector_panel["buttons"]) * self.CHAR_WIDTH)
        self.screen = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE)
        self.update_layout()

    def apply_drag_selection(self):
        if self.active_region and not self.active_region["is_top_bar"]:
            for i, button in enumerate(self.active_region["buttons"]):
                if self.is_in_drag_range(button["rect"].centerx):
                    button["enabled"] = not self.initial_states[i]

    def is_in_drag_range(self, x):
        if self.drag_start is None or self.drag_end is None:
            return False
        start_x, end_x = sorted([self.drag_start[0], self.drag_end[0]])
        return start_x <= x <= end_x

    def reset_drag_state(self):
        self.drag_start = self.drag_end = self.mouse_down_pos = self.active_region = None
        self.dragging = False
        self.dragging_slider = None

    def print_all_enabled(self):
        edo = base62_to_int(self.regions[0]["buttons"][self.selector_panel["selected"]])
        settings = {
            "EDO": edo,
            "ALL_UNIQUE_BINARIES1": [base62_to_int(b["label"]) for b in self.regions[1]["buttons"] if b["enabled"]],
            "ROTATIONS1": [base62_to_int(b["label"]) for b in self.regions[2]["buttons"] if b["enabled"]],
            "INTERVAL_VARIATIONS1": [base62_to_int(b["label"]) for b in self.regions[3]["buttons"] if b["enabled"]],
            "ALL_UNIQUE_BINARIES2": [base62_to_int(b["label"]) for b in self.regions[4]["buttons"] if b["enabled"]],
            "ROTATIONS2": [base62_to_int(b["label"]) for b in self.regions[5]["buttons"] if b["enabled"]],
            "INTERVAL_VARIATIONS2": [base62_to_int(b["label"]) for b in self.regions[6]["buttons"] if b["enabled"]]
        }

        # Convert selected binaries to the required format
        specific_chords1 = []
        specific_chords2 = []

        for i, chord_set in enumerate(self.chord_states1):
            for j, is_selected in enumerate(chord_set):
                if is_selected:
                    specific_chords1.append((i, j))

        for i, chord_set in enumerate(self.chord_states2):
            for j, is_selected in enumerate(chord_set):
                if is_selected:
                    specific_chords2.append((i, j))

        settings["SPECIFIC_CHORDS1"] = specific_chords1
        settings["SPECIFIC_CHORDS2"] = specific_chords2

        with open("settings.py", "w") as f:
            for key, value in settings.items():
                f.write(f"{key} = {value}\n")

        os.system("python edo_graphs2.py")
        self.load_symbols()

        self.slider_positions = {1: None, 4: None}
        self.scroll_offset = 0
        self.draw()

    def update_layout(self):
        self.calculate_window_size()
        self.update_selector_rects()
        self.regions = []
        self.create_regions()
        self.create_print_button()
        self.screen = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE)
        self.draw()

    def load_symbols(self):
        try:
            import symbols
            importlib.reload(symbols)
            self.symbols = symbols.SYMBOLS
        except ImportError:
            print("Error: Could not load symbols.py")
            self.symbols = []

    def run(self):
        clock = pygame.time.Clock()
        while self.handle_events():
            clock.tick(60)

if __name__ == "__main__":
    ChordSizeSelector().run()