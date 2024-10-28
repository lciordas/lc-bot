import random
import time
import multiprocessing
import json
'''processes = []
for _ in range(10):
    p = multiprocessing.Process(target=run_random_game)
    p.start()
    processes.append(p)

for process in processes:
    process.join()'''
#import concurrent.futures
from board import Board

board = Board()
board.set_board('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR')

white_score = [0, 0, 0]
black_score = [0, 0, 0]
checkmate_games = []

def run_random_game(file):
    white_score = [0, 0, 0]
    black_score = [0, 0, 0]
    checkmate_games = []

    for _ in range(500):
        board.set_board('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR')

        FEN_storage = []

        count = 0
        seventy_five_counter = 0
        while True:
            if count % 2 == 0: color = 'white'
            else:              color = 'black'

            # 75 move check
            if seventy_five_counter >= 75:
                white_score[1] += 1
                black_score[1] += 1

                print(count)
                print(board.board_to_FEN())
                print()
                break

            move_list = board.get_all_moves(color)


            if board.terminal_detect(color):
                if board.terminal_detect(color) in ['draw by stalemate', 'draw by insuficcient material']:
                    white_score[1] += 1
                    black_score[1] += 1

                    print(count)
                    print(board.board_to_FEN())
                    print()
                    break

                elif board.terminal_detect(color) == 'checkmate, white wins':
                    white_score[0] += 1
                    black_score[2] += 1
                    checkmate_games.append(board.board_to_FEN())

                    print(count)
                    print(board.board_to_FEN())
                    print()
                    break

                elif board.terminal_detect(color) == 'checkmate, black wins':
                    white_score[2] += 1
                    black_score[0] += 1
                    checkmate_games.append(board.board_to_FEN())

                    print(count)
                    print(board.board_to_FEN())
                    print()
                    break


            random_move = random.choice(move_list)

            formatted_move = board.parse_move(random_move)

            # 75 reset
            is_capture = False
            if board.num_to_piece_obj(formatted_move[1]):
                is_capture = True

            is_pawn_push = False
            if board.num_to_piece_obj(formatted_move[0]).piece_type == 'pawn':
                is_pawn_push = True

            if is_capture or is_pawn_push:
                seventy_five_counter = -1


            board.final_make_move(formatted_move[0], formatted_move[1], color)

            FEN_storage.append(board.board_to_FEN())

            
            # 5-fold check
            five_fold_count = 0
            current_pos = board.board_to_FEN()
            for FEN_pos in FEN_storage:
                if FEN_pos == current_pos:
                    five_fold_count += 1
            
            if five_fold_count >= 5:
                white_score[1] += 1
                black_score[1] += 1

                print(count)
                print(board.board_to_FEN())
                print()
                break

            count += 1
            seventy_five_counter += 1

    data_dic = {'white_score': white_score, 'black_score': black_score, 'checkmate_games': checkmate_games}
    
    with open(f'/Users/Lucasciordasna/Desktop/python_work/chess_engine/chess_engine2.0/data/{file}.json', 'w') as file:
        json.dump(data_dic, file, indent=4)



start = time.perf_counter()
if __name__ == '__main__':

    processes = []
    for i in range(20):
        p = multiprocessing.Process(target=run_random_game, args=[f'process{i+1}'])
        p.start()
        processes.append(p)

    for process in processes:
        process.join()

end = time.perf_counter()


print(f'White Record: {white_score}')
print(f'Black Record: {black_score}')
print()
print(f'Time taken: {round(end-start, 2)} seconds')

#cant redump to a file