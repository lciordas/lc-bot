import time
import random
import math
import statistics
import board
import evaluation
from copy import deepcopy
import pickle

evaluator = evaluation.KingSafetyEval()
board     = board.Board()

'''def mini_max_tree(node):
    if node.status == 'tosearch':
        parent    = node.parent
        value_list = [child.value for child in parent.children]

        if parent.color == 'white':
            parent.value = max(value_list)

        if parent.color == 'black':
            parent.value = min(value_list)
        
        for child in parent.children:
            child.status = 'completed'

        parent.status = 'tosearch'

    elif node.status == 'completed': return

    else:
        for child in node.children:
            mini_max_tree(child)'''


class Node:

    def __init__(self, color =None, move =None, parent =None, eval_ =None):
        self.color          = color
        self.move           = move
        self.parent         = parent
        self.children       = []
        self.eval           = eval_
        self.value          = None
        self.status         = None
        self.board_pos      = None
        self.internal_board = None


def check_for_termination(boardFEN):
        import board
        board = board.Board()
        board.set_board(boardFEN)

        white_moves = board.get_all_moves('white')
        black_moves = board.get_all_moves('black')

        white_in_check = board.check_board_for_checks('white')
        black_in_check = board.check_board_for_checks('black')

        if not white_moves and not white_in_check:
            return 'stalemate'
        if not black_moves and not black_in_check:
            return 'stalemate'
        if not white_moves and white_in_check:
            return 'black wins by checkmate'
        if not black_moves and black_in_check:
            return 'white wins by checkmate'


def check_for_check(boardFEN):
    import board
    board = board.Board()
    board.set_board(boardFEN)

    white_in_check = board.check_board_for_checks('white')
    black_in_check = board.check_board_for_checks('black')

    if white_in_check: return 'white in check'
    if black_in_check: return 'black in check'
    else: return None


def check_for_kings(boardFEN):
    kings_present = [False, False]
    for piece in boardFEN:
        if piece in '12345678/': continue
        if piece == 'K':
            kings_present[0] = True
        if piece == 'k':
            kings_present[1] = True
    if kings_present[0] == False:
        return 'white king gone'
    if kings_present[1] == False:
        return 'black king gone'


def make_move_tree(node, internal_board, depth, multiprocessing=False):
    import multiprocessing
    func_was_called_using_multiproccesing = False
    child_pipe_end = None
    if isinstance(node, tuple) and isinstance(internal_board[0], int):
        func_was_called_using_multiproccesing = True
        child_pipe_end = internal_board[1]
        #print('we know this func was called with one using multiprocessing')
        args = node
        node           = args[0]
        internal_board = args[1]
        depth          = args[2]
        #with open(f"pickle{internal_board}.pkl", "rb") as file:
        #    args = pickle.load(file)
        #    node           = args[0]
        #    internal_board = args[1]
        #    depth          = args[2]
            #print(node, internal_board, depth)
    
    print(node, internal_board, depth)
    print()


    import board
    board = board.Board()
    internal_board = deepcopy(internal_board)
    board.internal_board = internal_board
    boardFEN = board.board_to_FEN()

    node.board_pos = boardFEN
    node.internal_board = deepcopy(internal_board)

    if depth <= 0:
        #print('leaf node')
        eval_     = evaluator.evaluate(boardFEN)
        node.eval = eval_

        capturing_moves = get_capturing_moves(boardFEN, board.get_all_moves(node.color), node.color)
        if not capturing_moves: #position is quiet
            node.value  = node.eval
            return
        else: #position has captures
            #node.value  = node.eval

            #print(node.board_pos)
            make_capturing_move_tree(node, internal_board, 2)

            if node.color == 'white':
                if node.children:
                    if node.children[0].children:
                        if node.eval >= node.children[0].children[0].eval:
                            node.value = node.eval
                    else:
                        if node.eval >= node.children[0].eval:
                            node.value = node.eval
            
            if node.color == 'black':
                if node.children:
                    if node.children[0].children:
                        if node.eval <= node.children[0].children[0].eval:
                            node.value = node.eval
                    else:
                        if node.eval <= node.children[0].eval:
                            node.value = node.eval

            return


        # only do the below code if the position is quiet
        # need a function to check if a posision is quiet
        # if a potisition is not quiet --> make all the captures ultil it is quiet
        # do the captures extend like more layers or is it just one transformation of a
        # noisy position into a quiet one?

        # first evaluate the position anyway
        #  - (possible that player is winning but only has bad capture moves available)
        #  - this matters whose turn it is to move


        # check if the new search works by giving it position where bot previously blundered due to horizon effect

    moves_list = board.get_all_moves(node.color)
    ordered_moves_list = finally_ordered(deepcopy(node.internal_board), moves_list, node.color)
    #print(node.color)
    #print(node.board_pos)
    #print(moves_list)
    #print(len(moves_list))

    if node.color == 'white': opp_col = 'black'
    if node.color == 'black': opp_col = 'white'

    if multiprocessing:
        if __name__ == '__main__':
            import multiprocessing
            processes = []
            parent_pipe_ends = []
            count = 0
            for move in ordered_moves_list:
                #if count == 19:
                #    afnp3qkwgeowpmtke = True
                s_sqr = int(move.split('->')[0])
                e_sqr = int(move.split('->')[1])
                
                board.final_make_move(s_sqr, e_sqr, node.color)
                newFEN  = board.board_to_FEN()
                new_internal_board = deepcopy(board.internal_board)

                termination = check_for_termination(newFEN)
                if termination:
                    eval_    = evaluator.evaluate(newFEN)
                    new_node = Node(opp_col, move, node, eval_)
                    new_node.value     = new_node.eval
                    new_node.board_pos = newFEN
                    new_node.internal_board = deepcopy(new_internal_board)
                    node.children.append(new_node)
                    board.internal_board = deepcopy(node.internal_board)
                else:
                    eval_ = None
                    new_node = Node(opp_col, move, node, eval_)
                    new_node.board_pos = newFEN
                    #node.children.append(new_node)

                    args = [new_node, new_internal_board, depth-1]
                    if check_for_check(newFEN):
                        args[2] = depth
                    args = tuple(args)

                    #with open(f"pickle{count}.pkl", "wb") as file:
                    #    pickle.dump(args, file)
                    child_end, parent_end = multiprocessing.Pipe()
                    parent_pipe_ends.append(parent_end)
                    p = multiprocessing.Process(target=make_move_tree, args=[args, [count, child_end], ''])
                    p.start()
                    print('new proccess started')
                    
                    processes.append(p)

                    board.internal_board = deepcopy(node.internal_board)
                    count += 1
        if __name__ == '__main__':
            for parent_end in parent_pipe_ends:
                subtree_root = parent_end.recv()
                #parent_end.close()
                node.children.append(subtree_root)

            for process in processes:
                process.join()
                #proccess is done running here and sub tree has been generated
    
    else:
        for move in ordered_moves_list:
            ####150####150####150####150
            #if move not in ordered_moves_list[:3]:
            #    if depth == 3:
            #        depth = 2

            #print(move)
            s_sqr = int(move.split('->')[0])
            e_sqr = int(move.split('->')[1])
            #if board.num_to_piece_obj(s_sqr) == None:
            #    print(board.board_to_FEN())
            #    print(s_sqr, e_sqr)
            board.final_make_move(s_sqr, e_sqr, node.color)

            newFEN  = board.board_to_FEN()

            new_internal_board = deepcopy(board.internal_board)

            #print(newFEN)
            #if depth > 1:
                #print('going deeper...')
            #print()
        
            

            termination = check_for_termination(newFEN)
            if termination:
                #print('termination')
                # make the node but not any children from it
                eval_    = evaluator.evaluate(newFEN)
                new_node = Node(opp_col, move, node, eval_)            
                new_node.value     = new_node.eval
                new_node.board_pos = newFEN
                new_node.internal_board = deepcopy(new_internal_board)

                node.children.append(new_node)

                ##board.set_board(boardFEN)
                #board.internal_board = deepcopy(internal_board)
                #board.internal_board = internal_board
                board.internal_board = deepcopy(node.internal_board)


            else:
                #eval_    = evaluator.evaluate(newFEN)
                eval_ = None
                new_node = Node(opp_col, move, node, eval_)
                new_node.board_pos = newFEN

                node.children.append(new_node)

                # extend search by one layer if there is a check on the board
                if check_for_check(newFEN):
                    #print('in check')
                    ##make_move_tree(new_node, newFEN, depth)
                    ##board.set_board(boardFEN)
                    make_move_tree(new_node, new_internal_board, depth)
                    #board.internal_board = deepcopy(internal_board)
                    #board.internal_board = internal_board
                    board.internal_board = deepcopy(node.internal_board)

                else:
                    #print('clear of check')
                    ##make_move_tree(new_node, newFEN, depth-1)
                    ##board.set_board(boardFEN)
                    make_move_tree(new_node, new_internal_board, depth-1)
                    #board.internal_board = deepcopy(internal_board)
                    # board.internal_board = internal_board
                    board.internal_board = deepcopy(node.internal_board)
                    #bf = board.board_to_FEN()
                    #print(bf, 'bf')
                    #print()
                    #print(board.board_to_FEN())
            #board.internal_board = deepcopy(internal_board)
        
        # EACH CHILD PROCESS ENDS HERE
        if func_was_called_using_multiproccesing and child_pipe_end:
            print(node)
            child_pipe_end.send(node)
            child_pipe_end.close()
            # we now have the node
            # how do we send it?
            


def finally_ordered(internal_board, moves_list, color):
    #start = time.perf_counter()

    import board
    board = board.Board()
    #internal_board = deepcopy(internal_board)
    #board.internal_board = deepcopy(internal_board)
    board.internal_board = internal_board
    boardFEN = board.board_to_FEN()

    finally_ordered_list = []

    capturing_moves = MVV_LVA_ordered(internal_board, get_capturing_moves(boardFEN, moves_list, color), color)
    #print('capturing moves sorted')
    #capt = time.perf_counter()
    #print(capt-start, 'seconds')
    #checking_moves  = get_checking_moves(internal_board, moves_list, color)
    checking_moves = []
   # print('checking moves sorted')
    #chec = time.perf_counter()
    #print(chec-start, 'seconds')

    for move in moves_list:
        if move in capturing_moves or move in checking_moves:
            moves_list.remove(move)
    
    #print('extra moves removed')
    #rem = time.perf_counter()
    #print(rem-start, 'seconds')

    finally_ordered_list += capturing_moves
    finally_ordered_list += checking_moves
    finally_ordered_list += moves_list

    #print('function done')
    #end = time.perf_counter()
    #print(end-start, 'seconds')
    return finally_ordered_list
    
    

'''
# minimax function withought pruning but with crucial M1 ability
def mini_max_tree(node):
    # if node has no children or game is somehow over
    if not node.children:
        return node.value
    
    # MAXIMIZING PLAYER
    if node.color == 'white':
        max_eval = -5000000
        for child in node.children:
            val = mini_max_tree(child)
            max_eval = max(max_eval, val)
            node.value = max_eval

            if node.value > 100000:
                node.value -= 1

        return node.value

    # MINIMIZING PLAYER
    elif node.color == 'black':
        min_eval = 5000000
        for child in node.children:
            val = mini_max_tree(child)
            min_eval = min(min_eval, val)
            node.value = min_eval

            if node.value < -100000:
                node.value += 1

        return node.value'''

'''
# completely working, restructured minimax function with A/B pruning
def mini_max_tree(node, alpha, beta):
    # if node has no children or game is somehow over
    if not node.children:
        return node.value
    
    # MAXIMIZING PLAYER
    if node.color == 'white':
        max_eval = -5000000

        for child in node.children:
            val = mini_max_tree(child, alpha, beta)
            max_eval = max(max_eval, val)
            node.value = max_eval
            alpha = max(alpha, node.value)
            if alpha >= beta:
                break
        return node.value

    # MINIMIZING PLAYER
    elif node.color == 'black':
        min_eval = 5000000

        for child in node.children:
            val = mini_max_tree(child, alpha, beta)
            min_eval = min(min_eval, val)
            node.value = min_eval
            beta = min(beta, node.value)
            if alpha >= beta:
                break
        return node.value'''



'''
# restructured minimax, A/B pruning, M1 guarantee
def mini_max_tree(node, alpha, beta):
    # if leaf node
    if not node.children:
        return node.value
    
    # MAXIMIZING PLAYER
    if node.color == 'white':
        max_eval = -5000000

        for child in node.children:
            val = mini_max_tree(child, alpha, beta)
            max_eval = max(max_eval, val)
            node.value = max_eval
            alpha = max(alpha, node.value)
            if alpha >= beta:
                break
        if node.value > 100000:
            node.value -= 1
        return node.value

    # MINIMIZING PLAYER
    elif node.color == 'black':
        min_eval = 5000000

        for child in node.children:
            val = mini_max_tree(child, alpha, beta)
            min_eval = min(min_eval, val)
            node.value = min_eval
            beta = min(beta, node.value)
            if alpha >= beta:
                break
        if node.value < -100000:
            node.value += 1
        return node.value'''


'''# restructured minimax, A/B pruning, M1 guarantee, draw by repetition
def mini_max_tree(node, alpha, beta, draw_list):
    #print('minimaxing tree')
    # if leaf node
    if not node.children:
        return node.value

    # if repeated position
    if node.board_pos in draw_list:
        node.value = 0
        return node.value
    
    # MAXIMIZING PLAYER
    if node.color == 'white':
        max_eval = -5000000

        for child in node.children:
            val = mini_max_tree(child, alpha, beta, draw_list)
            max_eval = max(max_eval, val)
            node.value = max_eval
            alpha = max(alpha, node.value)
            if alpha >= beta:
                break
        if node.value > 100000:
            node.value -= 1
        return node.value

    # MINIMIZING PLAYER
    elif node.color == 'black':
        min_eval = 5000000

        for child in node.children:
            val = mini_max_tree(child, alpha, beta, draw_list)
            min_eval = min(min_eval, val)
            node.value = min_eval
            beta = min(beta, node.value)
            if alpha >= beta:
                break
        if node.value < -100000:
            node.value += 1
        return node.value'''

    
# restructured minimax, A/B pruning, M1 guarantee, draw by repetition, transposition table
def mini_max_tree(node, alpha, beta, draw_list):
    #print('minimaxing tree')
    # if leaf node
    if not node.children:
        return node.value

    # if repeated position
    if node.board_pos in draw_list:
        node.value = 0
        return node.value
    
    # MAXIMIZING PLAYER
    if node.color == 'white':
        max_eval = -5000000

        for child in node.children:
            val = mini_max_tree(child, alpha, beta, draw_list)
            max_eval = max(max_eval, val)
            node.value = max_eval
            alpha = max(alpha, node.value)
            if alpha >= beta:
                break
        if node.value > 100000:
            node.value -= 1
        return node.value

    # MINIMIZING PLAYER
    elif node.color == 'black':
        min_eval = 5000000

        for child in node.children:
            val = mini_max_tree(child, alpha, beta, draw_list)
            min_eval = min(min_eval, val)
            node.value = min_eval
            beta = min(beta, node.value)
            if alpha >= beta:
                break
        if node.value < -100000:
            node.value += 1
        return node.value



'''
# old minimax func withought A/B pruning but with repeated move = draw detection
def mini_max_tree(node, draw_FEN_list):
    if not node.children:
        return node.value
    else:
        child_values = []
        for child in node.children:
            val = mini_max_tree(child, draw_FEN_list)

            if child.board_pos in draw_FEN_list:
                val = 0
            child_values.append(val)

        if node.color == 'white':
            node.value = max(child_values)
            if node.value > 100000:
                node.value -= 1

        if node.color == 'black':
            node.value = min(child_values)
            if node.value < -100000:
                node.value += 1

        return node.value'''


def count_nodes(node, num_nodes):
    count = num_nodes
    count += 1
    for child in node.children:
        count += count_nodes(child, 0)
    return count


def mini_max_best_move(internal_board, color, draw_FEN_list):
    import board
    board = board.Board()
    internal_board = deepcopy(internal_board)
    board.internal_board = deepcopy(internal_board)
    boardFEN = board.board_to_FEN()

    eval_   = evaluator.evaluate(boardFEN)
    creator = Node(color, eval_=eval_)
    creator.board_pos = boardFEN

    DEPTH = 3
    make_move_tree(creator, internal_board, DEPTH, True)
    print('MOVE TREE GENERATION DONE')
    for c in creator.children:
        print(c.move)
    #print(creator.children)
    print(creator.children[0].children)
    print(creator.children[0].value)
    mini_max_tree(creator, -5000000, 5000000, draw_FEN_list)

    print(creator.children)
    
    '''if color == 'white':
        top3 = [child.value for child in creator.children[:3]]
        worst_of_3 = min(top3)
        for child in creator.children:
            if child not in top3:
                if child.value >= worst_of_3:
                    #print(child.move)
                    # give child a proper search of proper depth
                    child.children = []
                    start = int(child.move.split('->')[0])
                    end   = int(child.move.split('->')[1])
                    board.final_make_move(start, end, 'white')
                    #print(board.board_to_FEN())
                    new_internal_board = deepcopy(board.internal_board)
                    make_move_tree(child, deepcopy(new_internal_board), 2)
                    mini_max_tree(child, -5000000, 5000000, draw_FEN_list)
                    board.internal_board = deepcopy(internal_board)
                    #print(board.board_to_FEN())
    
    if color == 'black':
        top3 = [child.value for child in creator.children[:3]]
        worst_of_3 = max(top3)
        for child in creator.children:
            if child not in top3:
                if child.value <= worst_of_3:
                    #print(child.move)
                    # give child a proper search of proper depth
                    child.children = []
                    start = int(child.move.split('->')[0])
                    end   = int(child.move.split('->')[1])
                    board.final_make_move(start, end, 'black')
                    new_internal_board = deepcopy(board.internal_board)
                    make_move_tree(child, deepcopy(new_internal_board), 2)
                    mini_max_tree(child, -5000000, 5000000, draw_FEN_list)
                    board.internal_board = deepcopy(internal_board)'''


    #nodes_searched = count_nodes(creator, 0)
    #print('Nodes searched:', nodes_searched)
    
    for child in creator.children:
        if creator.color == 'white':
            if creator.value > 100000:
                if child.value == creator.value + 1:
                    best_move = child.move
                    #print('whitemate')
                    return best_move
            else:
                if child.value == creator.value:
                    best_move = child.move
                    #print('whitenonmate')
                    return best_move

        elif creator.color == 'black':
            if creator.value < -100000:
                if child.value == creator.value - 1:
                    best_move = child.move
                    #print('blackmate')
                    return best_move
            else:
                if child.value == creator.value:
                    best_move = child.move
                    #print('blacknonmate')
                    return best_move



def random_move(boardFEN, color):
    import board
    board = board.Board()
    board.set_board(boardFEN)

    all_moves   = board.get_all_moves(color)
    random_move = random.choice(all_moves)
    return random_move


def get_piece_count(boardFEN):
    piece_count = 0
    for piece in boardFEN:
        if piece in '12345678/': continue
        piece_count += 1
    
    return piece_count


def get_checking_moves(internal_board, moves_list, color):
    import board
    board = board.Board()
    internal_board = deepcopy(internal_board)
    board.internal_board = deepcopy(internal_board)
    boardFEN = board.board_to_FEN()

    checking_moves = []
    
    for move in moves_list:
        start = int(move.split('->')[0])
        end   = int(move.split('->')[1])
        board.final_make_move(start, end, color)

        newFEN = board.board_to_FEN()

        if check_for_check(newFEN):
            checking_moves.append(move)
        board.internal_board = deepcopy(internal_board)
    
    return checking_moves


def get_capturing_moves(boardFEN, moves_list, color):
    import board
    board = board.Board()
    board.set_board(boardFEN)

    capturing_moves = []

    initial_piece_num = get_piece_count(boardFEN)

    for move in moves_list:
        start = int(move.split('->')[0])
        end   = int(move.split('->')[1])

        board.final_make_move(start, end, color)
        newFEN = board.board_to_FEN()

        final_piece_num = get_piece_count(newFEN)

        if final_piece_num == initial_piece_num - 1:
            capturing_moves.append(move)

        board.set_board(boardFEN)
    
    return capturing_moves
        

def make_capturing_move_tree(node, internal_board, depth):
    #print('making capturing move tree')
    import board
    board = board.Board()
    internal_board = deepcopy(internal_board)
    board.internal_board = internal_board
    boardFEN = board.board_to_FEN()

    node.board_pos = deepcopy(boardFEN)
    node.internal_board = deepcopy(internal_board)

    if node.color == 'white': opp_col = 'black'
    if node.color == 'black': opp_col = 'white'

    capturing_moves = get_capturing_moves(boardFEN, board.get_all_moves(node.color), node.color)
    #print(capturing_moves)
    if len(capturing_moves) > 1:
        sorted_capturing_moves = MVV_LVA_ordered(internal_board, capturing_moves, node.color)
    else:
        sorted_capturing_moves = capturing_moves
    #print(sorted_capturing_moves)

    if depth <= 0:
        node.value = node.eval
        return

    if not sorted_capturing_moves:
        node.value = node.eval
        #print('leaf node')
        return

    # to change num of moves you go thru change the sorted_capturing_moves index
    for move in sorted_capturing_moves[:1]:
        start = int(move.split('->')[0])
        end   = int(move.split('->')[1])

        board.final_make_move(start, end, node.color)

        new_internal_board = deepcopy(board.internal_board)
        newFEN = board.board_to_FEN()

        eval_    = evaluator.evaluate(newFEN)
        new_node = Node(opp_col, move, node, eval_)
        new_node.board_pos = newFEN
        new_node.internal_board = new_internal_board

        node.children.append(new_node)

        termination = check_for_termination(newFEN)
        if termination:
            #board.internal_board = internal_board
            board.internal_board = deepcopy(node.internal_board)
            #board.set_board(boardFEN)
            new_node.value = new_node.eval
            return
        else:
            make_capturing_move_tree(new_node, new_internal_board, depth-1)
            #board.internal_board = internal_board
            board.internal_board = deepcopy(node.internal_board)
            #board.set_board(boardFEN)


def MVV_LVA_ordered(internal_board, moves_list, color):
    import board
    board = board.Board()
    #internal_board = deepcopy(internal_board)
    #board.internal_board = deepcopy(internal_board)
    board.internal_board = internal_board
    boardFEN = board.board_to_FEN()

    MVV_LVA_table = [
            [0, 0, 0, 0, 0, 0],
            [50, 51, 52, 53, 54, 55],
            [40, 41, 42, 43, 44, 45],
            [30, 31, 32, 33, 34, 35],
            [20, 21, 22, 23, 24, 25],
            [10, 11, 12, 13, 14, 15],
            [0, 0, 0, 0, 0, 0],
        ]

    piecetype_to_index_map = {
        'king'  : 0,
        'queen' : 1,
        'rook'  : 2,
        'bishop': 3,
        'knight': 4,
        'pawn'  : 5,
        None    : 6
    }

    MVV_LVA_moves = []

    for move in moves_list:
        start = int(move.split('->')[0])
        end   = int(move.split('->')[1])

        try:
            victim       = board.num_to_piece_obj(end)
            v_piece_type = victim.piece_type
        except:
            v_piece_type = None

        attacker     = board.num_to_piece_obj(start)
        a_piece_type = attacker.piece_type

        v_indx = piecetype_to_index_map[v_piece_type]
        a_indx = piecetype_to_index_map[a_piece_type]
        MVV_LVA_val = MVV_LVA_table[v_indx][a_indx]

        duo = [move, MVV_LVA_val]
        MVV_LVA_moves.append(duo)

    def by_score(duo):
        return duo[1]

    MVV_LVA_moves = sorted(MVV_LVA_moves, key=by_score, reverse=True)
    MVV_LVA_moves = [x[0] for x in MVV_LVA_moves]

    return MVV_LVA_moves




# def mark_nodes_as_drawn(node, FEN_pos_list):
#     if node.board_pos in FEN_pos_list:
#         node.value = 0
#     if not node.children:
#         return
#     else:
#         for child in node.children:
#             mark_nodes_as_drawn(child, FEN_pos_list)



    # for child in creator.children:
    #     if child.value < 100000:
    #         if child.value == creator.value:
    #             child.move = best_move
    #         return best_move
    #     elif child.value > 100000:
    #         if child.value == creator.value + 1:
    #             pass

    # identical_moves = []
    # for child in creator.children:
    #     if child.value == creator.value:
    #         identical_moves.append(child)
    
    # for child in identical_moves:
    #     # find shallowest move
    #     pass
    
    # child_vals = []
    # val_and_obj_list = []
    # for child in creator.children:
    #     val_and_obj = []
    #     val_and_obj.append(child)
    #     val_and_obj.append(child.value)
    #     child_vals.append(child.value)
    #     val_and_obj_list.append(val_and_obj)
    
    # if creator.color == 'white':
    #     for val_and_obj in val_and_obj_list:
    #         if val_and_obj[1] == max(child_vals):
    #             best_move = val_and_obj[0].move
    #             return best_move
    # if creator.color == 'black':
    #     for val_and_obj in val_and_obj_list:
    #         if val_and_obj[1] == min(child_vals):
    #             best_move = val_and_obj[0].move
    #             return best_move

    # return best_move

    # # for child in creator.children:
    #     print(child.value)
    #     if child.value == creator.value:
    #         best_move = child.move
    #     elif abs(child.value) > 100000 and abs(child.value - creator.value) == 1:
    #         #print('OGOANELRFSOUEJL')
    #         #print(creator.value)
    #         #print(child.value)
    #         best_move = child.move
    # print()
    # print(creator.children[12].move)
    # print(creator.children[12].value)
    # for c in creator.children[12].children:
    #    print(c.value)


    # return best_move


# instead of traversing the tree recursivelt to fins the shallowest mode with identical value
# just subtract from the node when constructing hte move tree
# so it'll be 1,000,000 --> 999,999 --> 999,998 etc.


# def choose_shortest_same_val_depth(nodes_list):
#     shortest_node = None
#     for node in nodes_list:
#         depth = 0

#         if node.sv_depth < shortest_node.sv_depth: shortest_node = node
#         depth = 0




# def get_same_val_depth(node, depth=0):
#     val = node.value
#     if not node.children: return depth
#     depth += 1
#     same_vals = []
#     for child in node.children:
#         if child.value == val:
#             same_vals.append(child)

#     for child in same_vals:
#         get_same_val_depth(child, depth)


    # for child in creator.children:
    #         if child.value == creator.value:
    #             son = child
    #             best_move = child.move
    #     print('creator')
    #     print(creator.value)
    #     print(creator.move)
    #     print()
    #     print('son')
    #     print(son.value)
    #     print(son.move)
    #     print()
    #     for childd in son.children:
    #         if childd.value == son.value:
    #             son2 = childd
    #     print('son2')
    #     print(son2.value)
    #     print(son2.move)
    #     print()
    #     for childdd in son2.children:
    #         if childdd.value == son2.value:
    #             son3 = childdd
    #     print('son3')
    #     print(son3.value)
    #     print(son3.move)
    #     return best_move







def run_bot_game(internal_board, white_gen, black_gen):
    print('run_bot_game func')
    import board
    board = board.Board()
    internal_board = deepcopy(internal_board)
    board.internal_board = internal_board
    FENpos = board.board_to_FEN()
    #board.set_board(FENpos)

    all_board_pos = set()

    occured_moves = []
    #occured_moves = ['rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR', 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR', 'rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR', 'rnbqkbnr/pppp1ppp/8/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R', 'r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R', 'r1bqkbnr/pppp1ppp/2n5/1B2p3/4P3/5N2/PPPP1PPP/RNBQK2R']

    while True:

        if check_for_termination(FENpos):
            print(check_for_termination(FENpos))
            break

        # WHITE GEN TYPES
        if white_gen == 'minimax':
            move  = mini_max_best_move(internal_board, 'white', all_board_pos)
            start = int(move.split('->')[0])
            end   = int(move.split('->')[1])

            board.final_make_move(start, end, 'white')
            occured_moves.append(move)

            all_board_pos.add(FENpos)
            FENpos = board.board_to_FEN()

        elif white_gen == 'random':
            move  = random_move(FENpos, 'white')
            start = int(move.split('->')[0])
            end   = int(move.split('->')[1])

            board.final_make_move(start, end, 'white')
            occured_moves.append(move)

            all_board_pos.add(FENpos)
            FENpos = board.board_to_FEN()

        elif white_gen == 'input':
            move = input('Your move: ')
            start = int(move.split('->')[0])
            end   = int(move.split('->')[1])

            board.final_make_move(start, end, 'white')
            occured_moves.append(move)

            all_board_pos.add(FENpos)
            FENpos = board.board_to_FEN()

        print(occured_moves[-1])
        
        if check_for_termination(FENpos):
            print(occured_moves[-1])
            print(check_for_termination(FENpos))
            break


        # BLACK GEN TYPES
        if black_gen == 'minimax':
            move  = mini_max_best_move(internal_board, 'black', all_board_pos)
            start = int(move.split('->')[0])
            end   = int(move.split('->')[1])

            board.final_make_move(start, end, 'black')
            occured_moves.append(move)


            all_board_pos.add(FENpos)
            FENpos = board.board_to_FEN()

        elif black_gen == 'random':
            move  = random_move(FENpos, 'black')
            start = int(move.split('->')[0])
            end   = int(move.split('->')[1])

            board.final_make_move(start, end, 'black')
            occured_moves.append(move)

            all_board_pos.add(FENpos)
            FENpos = board.board_to_FEN()

        elif black_gen == 'input':
            move = input('Your move: ')
            start = int(move.split('->')[0])
            end   = int(move.split('->')[1])

            board.final_make_move(start, end, 'black')
            occured_moves.append(move)

            all_board_pos.add(FENpos)
            FENpos = board.board_to_FEN()

        print(f"{math.floor(len(occured_moves)/2)}. {occured_moves[-2]} {occured_moves[-1]}")








'''def run_bot_game(FENpos):
    import board
    board = board.Board()
    board.set_board(FENpos)

    all_board_pos = set()

    printed_moves = [0, 0]
    while True:
        # break if its checkmate or stalemate
        if check_for_termination(FENpos):
            if check_for_termination(FENpos) == 'white wins by checkmate':
                print(printed_moves[0])
            print(check_for_termination(FENpos))
            break

        if len(all_board_pos) % 2 == 0:
            color = 'white'
            gen_type = 'minimax'

        if len(all_board_pos) % 2 == 1:
            color = 'black'
            gen_type = 'random'


        #gen_type = input('How would you like to generate the next move?\n')
        if gen_type == 'minimax':
            move  = mini_max_best_move(FENpos, color, all_board_pos)
            start = int(move.split('->')[0])
            end   = int(move.split('->')[1])

            board.final_make_move(start, end, color)

            all_board_pos.add(FENpos)
            FENpos = board.board_to_FEN()

            if color == 'white':
                printed_moves[0] = move
            elif color == 'black':
                printed_moves[1] = move
                print(f'{math.floor(len(all_board_pos)/2)}. {printed_moves[0]} {printed_moves[1]}')

        elif gen_type == 'random':
            move  = random_move(FENpos, color)
            start = int(move.split('->')[0])
            end   = int(move.split('->')[1])

            board.final_make_move(start, end, color)

            all_board_pos.add(FENpos)
            FENpos = board.board_to_FEN()

            printed_moves[1] = move
            print(f'{math.floor(len(all_board_pos)/2)}. {printed_moves[0]} {printed_moves[1]}')'''


if __name__ == '__main__':
    start = time.perf_counter()
    import board
    board = board.Board()
    board.set_board('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR')
    #board.set_board('rnbqkbnr/pp2pppp/2pp4/8/4P3/2N5/PPPP1PPP/R1BQKBNR')
    #moves = board.get_all_moves('white')
    #for i in range(1000):
    #    x = finally_ordered(board.internal_board, moves, 'white')
    run_bot_game(board.internal_board, 'minimax', 'input')
    end   = time.perf_counter()
    print(round(end-start, 2), 'seconds')

#run_bot_game('r3kbr1/pN2ppp1/n2p4/2p4p/4P3/2NP4/PPP2PPP/R1BQKB1R')
#run_bot_game('rnbqrkb1/pp2pppp/3p4/2p5/4P3/2N2N2/PPP1PPPP/R1BQKB1R')
#'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR'
#'rnbqkbnr/pp2pppp/3p4/2p5/4P3/5N2/PPPP1PPP/RNBQKB1R'
#'r1bqkbnr/1ppp1ppp/p1n5/1B2p3/4P3/5N2/PPPP1PPP/RNBQK2R'
# start = time.perf_counter()

# FENpos = '8/8/5K2/8/r1k5/8/5Q2/8'

# print(mini_max_best_move(FENpos, 'white'))

# end   = time.perf_counter()
# print(round(end-start, 2), 'seconds')




# 3 THINGS TO ADD
#
# 1.) go thru every child, and if many children have the same value, choose shortest path
# 2.) assign value of 0 to a move that would repeat an already occured board position
#
# not #3 --> gonna just make moves already evaluated moves if the opponent make good moves
# in the move tree, but don't want to do that because want to reevaluate with extra depth