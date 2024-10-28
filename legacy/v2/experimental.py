def get_all_moves(self, color):
        master_list = []
        for i in range(1, 65):
            piece = self.num_to_piece_obj(i)
            if piece and piece.color == color:
                piece.get_moves()
                legal_list = self.dic_w_lists_to_list(piece.legal_moves)
                if piece.piece_type == 'king':
                    for move in legal_list:
                        if self.basic_rules(piece.pos, move) and self.K_special_rules(piece.pos, move) in [True, 'kingside_castle', 'queenside_castle']:
                            move_notation = str(piece.pos) + '->' + str(move)
                            master_list.append(move_notation)

                elif piece.piece_type in ['queen', 'rook', 'bishop']:
                    for move in legal_list:
                        if self.basic_rules(piece.pos, move) and self.QRB_special_rules(piece.pos, move) in [True]:
                            move_notation = str(piece.pos) + '->' + str(move)
                            master_list.append(move_notation)
                
                elif piece.piece_type == 'knight':
                    for move in legal_list:
                        if self.basic_rules(piece.pos, move):
                            move_notation = str(piece.pos) + '->' + str(move)
                            master_list.append(move_notation)

                elif piece.piece_type == 'pawn':
                    for move in legal_list:
                        if self.basic_rules(piece.pos, move) and self.P_special_rules(piece.pos, move) in [True, 'two_square_move', 'white_promotion', 'black_promotion', 'left_en_passant', 'right_en_passant']:
                            move_notation = str(piece.pos) + '->' + str(move)
                            master_list.append(move_notation)
                                
        return master_list