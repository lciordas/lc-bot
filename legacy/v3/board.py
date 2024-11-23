FEN_TO_UNICODE = {
    "K": "♚",
    "Q": "♛",
    "R": "♜",
    "B": "♝",
    "N": "♞",
    "P": "♟",
    "k": "♔",
    "q": "♕",
    "r": "♖",
    "b": "♗",
    "n": "♘",
    "p": "♙"
}

full_fen = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'

piece_placement, side_to_move, castling_rights, ep_square, hm_clock, fm_counter = full_fen.split()

board = []


def set_board_from_fen(piece_placement):
    """
        Fills the internal board (2d array) with pieces based off of the first part of the fen string.

        Args:
            piece_placement (str): A string of piece positions where each row is separated by a '/'.

        Returns:
            board (list): A list of 8 lists which each represent a row on the chessboard.
                          They contain 8 entries with either the letter of a piece on the square
                          or 'None' if the square is empty.
    """
    board = []
    for row in piece_placement.split('/'):
        board_row = []
        for char in row:
            if char.isdigit():
                board_row.extend([None] * int(char))
            else:
                board_row.append(char)
        board.append(board_row)
    return board


def get_fen(piece_placement, side_to_move, castling_rights, ep_square, hm_clock, fm_counter):
    """
        Construct a full FEN string from its six fields.

        Args:
            piece_placement (str): A string of piece positions where each row is separated by a '/'
            side_to_move (str): 'w' or 'b' indicating which side moves next
            castling_rights (str): Castling availability for each color (w = caps, b = lower)
                                and on which side (eg. 'KQkq' or '-')
            ep_square (str): En Passant target square or '-'
            hm_clock (int): Halfmove clock to trigger a draw at 100
            fm_counter (int): Number of full moves played (1 fm = 1 move for each player)

        Returns:
            str: The full FEN string representing the chess position.
    """
    full_fen = f"{piece_placement} {side_to_move} {castling_rights} {ep_square} {hm_clock} {fm_counter}"
    return full_fen


def get_piece_placement_from_board(board):
    """
        Get the piece placement fen string from the setup of the internal board.

        Args:
            board (list): The internal board representation with all pieces in each square.

        Returns:
            piece_placement (str): Describes the piece positioning on the board.
    """
    piece_placement_l = []
    for row in board:
        row_str = ''
        empty_count = 0
        for piece in row:
            if piece:
                if empty_count:
                    row_str += str(empty_count)
                    empty_count = 0
                row_str += piece
            else:
                empty_count += 1
        if empty_count:
            row_str += str(empty_count)
        piece_placement_l.append(row_str)
    piece_placement = '/'.join(piece_placement_l)
    return piece_placement


def render_board(board):
    """
        Render a chess board visually in the terminal using Unicode chess piece symbols.

        Args:
            board (list): The internal board containing all pieces positioned on given squares.

        Prints:
            The chess board.
    """
    for rank in range(8):
        print(8-rank, end='')
        for piece in board[rank]:
            print(f'|{FEN_TO_UNICODE[piece]}' if piece else '|_', end='')
        print('|')
    print('  a b c d e f g h')
    

def square_to_coords(square):
    """
        Translate chess square notation into number coordinates to access squares on internal board.

        Args:
            square (str): A letter followed by a number that describes a square on the board.
                          eg. 'b3'

        Returns:
            coords (tuple): A tuple with 2 coordinates to access first the row and then the square.
                            eg. (5, 1)
    """
    rank = 8 - int(square[1])
    file = ord(square[0]) - ord('a') # The ord() func returns unicode number associated with a character.
                                     # Since a,b,c are numbered consecutively, subtracting the num of 'a'
                                     # from the nums of letters a-h yields numbers 0-7.
    coords = (rank, file)
    return coords


def make_move(board, start_square, end_square):
    """
        Make a move on the internal board (without regard to legality) as long as:
            - There is a piece on the start square
            - The end square is different from the start square
        Doesn't check for legality, simple makes the move (as long as there is a piece on the start
        square and the start square is different from the end square).

        Args:
            board (list): The internal board pieces on each square.
            start_square (str): Algebraic notation like 'e3'.
            end_square (str): Algebraic notation like 'h8'.

        Returns:
            None (updates the board that was input but doesn't return anything).
    """
    starting_rank, starting_file = square_to_coords(start_square)
    ending_rank  , ending_file   = square_to_coords(end_square)

    piece = board[starting_rank][starting_file]
    if not piece:
        print(f"[make_move] Error: There is no piece to move on {start_square}.")
        return
    if start_square == end_square:
        print(f"[make_move] Error: End square ({end_square}) cannot be the same as start square ({start_square}).")
        return
    board[ending_rank][ending_file] = piece
    board[starting_rank][starting_file] = None


board = set_board_from_fen(piece_placement)
render_board(board)

while True:
    i = input('Enter start and end squares: ')
    s, e = i.split()

    make_move(board, s, e)
    render_board(board)