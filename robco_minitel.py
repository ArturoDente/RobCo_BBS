import asyncio
import random
import telnetlib3
import sys

# Costanti per i colori ANSI
ANSI_RESET = '\x1b[0m'
ANSI_BOLD = '\x1b[1m'
ANSI_CYAN = '\x1b[36m'
ANSI_YELLOW = '\x1b[33m'
ANSI_WHITE = '\x1b[37m'
ANSI_GREEN = '\x1b[32m'

# Le "schermate" di parole pronte
PAROLE_SCHERMATE = [
    ["holding", "healing", "traders", "lending", "physics", "options", "bandits", "winding", "driving", "barrens", "sermons"],
    ["feature", "theater", "rescued", "decorum", "uniform", "forming", "gearing", "arising", "neutral", "reading", "tension"],
    ["lending", "gateway", "western", "running", "gaining", "engaged", "dangers", "survive", "venture", "rebuild", "delight"],
    ["folding", "glacier", "respect", "treacle", "learner", "restore", "recline", "neutral", "lattice", "ceramic", "caution"],
    ["capture", "reality", "tending", "grinder", "relying", "glowing", "gateway", "wayward", "distant", "tangled", "delight"],
    ["breathe", "harness", "serpent", "tending", "garland", "dashing", "glimmer", "remains", "sparing", "genesis", "silence"],
    ["paragon", "gnawing", "grasped", "draping", "garment", "tending", "glisten", "network", "kindred", "dressed", "serpent"],
    ["blazing", "glasses", "serious", "unequal", "lateral", "glacier", "regrets", "stretch", "horizon", "nesting", "railing"],
    ["branded", "delight", "thrives", "decorum", "gateway", "lending", "garment", "tending", "respect", "draping", "serious"],
    ["folding", "glances", "serious", "uniform", "formula", "lending", "restore", "revenue", "endless", "tenders", "glimmer"]
]

CARATTERI_CASUALI = '!@#$%^&*()_+-=[]{}|;:",.<>/?~`'

def get_likeness(guess, password):
    """Calcola il numero di lettere in comune nella stessa posizione."""
    likeness = 0
    for g_char, p_char in zip(guess, password):
        if g_char == p_char:
            likeness += 1
    return likeness

def generate_junk_string(length):
    """Genera una stringa casuale di caratteri 'spazzatura'."""
    return ''.join(random.choice(CARATTERI_CASUALI) for _ in range(length))

def get_robco_splash():
    """Restituisce il splash screen con logo RobCo compatto."""
    return (
        f"{ANSI_GREEN}{ANSI_BOLD}"
        f"\r\n"
        r"     ____       _     ____    "
        f"\r\n"
        r"    |  _ \ ___ | |__ / ___| ___ "
        f"\r\n"
        r"    | |_) / _ \| '_ \| |   / _ \ "
        f"\r\n"
        r"    |  _ < (_) | |_) | |__| (_) |"
        f"\r\n"
        r"    |_| \_\___/|_.__/ \____\___/ "
        f"\r\n"
        f"\r\n   Industries Terminal Systems"
        f"\r\n"
        f"\r\n      TERMINAL HACKING SYSTEM v2.1.7"
        f"\r\n      Copyright 2287 RobCo Industries"
        f"\r\n"
        f"\r\n      * AUTHORIZED ACCESS ONLY *"
        f"\r\n"
        f"\r\n      +---------------------------+"
        f"\r\n"
        r"      | Press any key to continue |"
        f"\r\n"
        r"      +---------------------------+"
        f"\r\n"
        f"{ANSI_RESET}"
    )

def generate_game_screen(words, junk_fill_ratio=0.5):
    """
    Genera la schermata di gioco mescolando parole e "spazzatura".
    Restituisce una lista di stringhe formattate con indirizzo esadecimale.
    """
    all_content = []
    
    for word in words:
        all_content.append(word)

    num_junk_strings = int(len(words) / (1 - junk_fill_ratio) - len(words))
    for _ in range(num_junk_strings):
        all_content.append(generate_junk_string(7))

    random.shuffle(all_content)

    screen = []
    for i in range(0, len(all_content), 2):
        if i + 1 < len(all_content):
            address = f"{1024 + i * 16:04X}"
            line = f"0x{address} {all_content[i]} {all_content[i+1]}"
            screen.append(line)
        else:
            address = f"{1024 + i * 16:04X}"
            line = f"0x{address} {all_content[i]}"
            screen.append(line)

    return screen

async def handle_telnet(reader, writer):
    """Logica di gioco del server con gestione migliorata delle disconnessioni."""
    # Invia i comandi di negoziazione Telnet richiesti dal client Minitel
    writer.transport.write(b'\xff\xfb\x01')  # IAC WILL ECHO
    writer.transport.write(b'\xff\xfb\x03')  # IAC WILL SUPPRESS-GO-AHEAD
    # Il resto della negoziazione (e.g., TTYPE) è gestita automaticamente da telnetlib3.
    
    try:
        # Questo ciclo infinito permette di ricominciare il gioco dopo ogni fine partita
        while True:
            # Codice per la splash screen
            if not writer.is_closing():
                writer.write('\x1b[2J\x1b[H') # Pulisce lo schermo
                writer.write(get_robco_splash()) # Richiama la funzione
                await writer.drain()
                await reader.read(1) # Attende la pressione di un tasto

            # Resetta le variabili di gioco per la nuova partita
            chosen_screen_words = random.choice(PAROLE_SCHERMATE)
            password = random.choice(chosen_screen_words)
            total_attempts = 4
            attempts_made = 0
            
            guess_history = []
            
            screen_lines = generate_game_screen(chosen_screen_words)
            num_lines = len(screen_lines)

            def is_connection_alive():
                """Verifica se la connessione è ancora attiva."""
                return not writer.is_closing() and not reader.at_eof()

            async def safe_write(data):
                """Scrive dati in modo sicuro, gestendo le disconnessioni."""
                try:
                    if is_connection_alive():
                        writer.write(data)
                        await writer.drain()
                        return True
                except (OSError, IOError, ConnectionResetError, BrokenPipeError, asyncio.IncompleteReadError):
                    print(f"Error during writing")
                    return False
                return False

            async def safe_readline():
                """Legge una riga con echo dei caratteri digitati."""
                try:
                    if is_connection_alive():
                        input_buffer = ""
                        while True:
                            char = await reader.read(1)
                            if not char:  # Connessione chiusa
                                return None
                            
                            # Gestisci caratteri speciali
                            if char == '\r' or char == '\n':
                                writer.write('\r\n')
                                await writer.drain()
                                return input_buffer.strip().lower()
                            elif char == '\b' or ord(char) == 127:  # Backspace o DEL
                                if input_buffer:
                                    input_buffer = input_buffer[:-1]
                                    writer.write('\b \b')  # Cancella carattere visivamente
                                    await writer.drain()
                            elif ord(char) >= 32 and ord(char) <= 126:  # Caratteri stampabili
                                input_buffer += char
                                writer.write(char)  # Echo del carattere
                                await writer.drain()
                                
                    return None
                except (OSError, IOError, ConnectionResetError, BrokenPipeError, asyncio.IncompleteReadError):
                    print(f"Error during reading")
                    return None
                
            print(f"New connection established. Password: {password}")
            
            while attempts_made < total_attempts and is_connection_alive():
                # Pulisci schermo
                if not await safe_write('\x1b[2J\x1b[H'):
                    break
                    
                if not await safe_write(
                    "RobCo industries (tm) termlink protocol \n\r "
                    "Enter password now.\n\r\n\r"
                ):
                    break
                
                # Mostra la schermata di gioco
                for i, line in enumerate(screen_lines):
                    if not is_connection_alive():
                        break
                        
                    attempt_display = ""
                    if i >= num_lines - total_attempts:
                        attempt_index = i - (num_lines - total_attempts)
                        if attempt_index < len(guess_history):
                            guessed_word, likeness = guess_history[attempt_index]
                            attempt_display = f"{guessed_word} ({likeness}/{len(password)})"
                    
                    if not await safe_write(f"{line:<25}{attempt_display:<14}\n\r"):
                        break

                if not is_connection_alive():
                    break

                if not await safe_write(
                    f"\n\rAttempts remaining: {total_attempts - attempts_made}\n\r"
                    "Enter password (or '.' to exit): "
                ):
                    break

                # Leggi input utente
                guess = await safe_readline()
                
                if guess is None:  # Errore di lettura o disconnessione
                    break
                    
                if not guess:
                    continue

                if guess == '.':
                    break

                # Pulisci schermo per il risultato
                if not await safe_write('\x1b[2J\x1b[H'):
                    break

                if guess == password:
                    win_message = "Access granted!"
                    password_message = f"The password was: {password}"
                    max_len = 35
                    border = '*' * max_len

                    await safe_write(
                        f"\n\r"
                        f"{border}\n\r"
                        f"*{win_message.center(max_len-2)}*\n\r"
                        f"*{password_message.center(max_len-2)}*\n\r"
                        f"{border}\n\r"
                    )
                    break
                elif guess in chosen_screen_words:
                    likeness = get_likeness(guess, password)
                    if not await safe_write(
                        f"\n\rPassword not correct. \n\r"
                        f"[{likeness}/{len(password)}] letters correct.\n\r"
                    ):
                        break
                    guess_history.append((guess, likeness))
                    attempts_made += 1
                else:
                    if not await safe_write(f"\n\rPassword not recognized. Not in the list.\n\r"):
                        break
                    attempts_made += 1
                
                # Pausa solo se la connessione è ancora attiva
                if is_connection_alive():
                    await asyncio.sleep(2)

            # Messaggi finali dopo la fine della partita
            if is_connection_alive():
                if attempts_made == total_attempts:
                    fail_message_1 = "Attempts exhausted!"
                    password_message = f"The password was: {password}"
                    fail_message_2 = "Terminal locked."
                    max_len = 35
                    border = '*' * max_len

                    await safe_write(
                        f"\n\r"
                        f"{border}\n\r"
                        f"*{fail_message_1.center(max_len-2)}*\n\r"
                        f"*{password_message.center(max_len-2)}*\n\r"
                        f"*{fail_message_2.center(max_len-2)}*\n\r"
                        f"{border}\n\r"
                    )
                
                await safe_write("\n\rThank you for playing. Press any key to play again or '.' to exit...\n\r")
                
                # Attende l'input dell'utente prima di resettare o chiudere
                final_choice = await safe_readline()
                if final_choice is None or final_choice == '.':
                    break # Esce dal ciclo principale, chiudendo la connessione
            else:
                break # Esce se la connessione non è più attiva
    
    except (OSError, IOError, ConnectionResetError, BrokenPipeError, asyncio.IncompleteReadError) as e:
        print("Il client si è disconnesso in modo inaspettato.")
    except Exception as e:
        print(f"Si è verificato un errore imprevisto: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Chiusura sicura della connessione
        try:
            if not writer.is_closing():
                writer.close()
        except Exception as e:
            print(f"Errore durante la chiusura del writer: {e}")
        
        print("Sessione terminata.")


async def main():
    """Avvia il server telnet e lo mantiene in esecuzione."""
    print("Starting RobCo Terminal server on port 6023...")
    
    server = await telnetlib3.create_server(
        port=6023,
        shell=handle_telnet,
        encoding='utf-8'
    )
    
    print("Server started! Listening on port 6023")
    print("Press Ctrl+C to stop the server")
    
    try:
        await server.serve_forever()
    except asyncio.CancelledError:
        print("\nThe server was interrupted. Shutting down...")
    except KeyboardInterrupt:
        print("\nKeyboard interruption detected. Shutting down the server...")
    finally:
        print("Closing the server...")
        server.close()
        await server.wait_closed()
        print("Server closed.")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer closed by user.")
    except Exception as e:
        print(f"An unexpected error occurred in the server: {e}")
        import traceback
        traceback.print_exc()