from typing import Tuple, Optional, List, Dict
import math
import random


def get_utility_2d(board: Tuple[Optional[int], ...]) -> Optional[int]:

    # check rows and cols
    for i in range(4):

        # columns
        column = board[i:16:4]
        if (column[0] and column.count(column[0]) == 4):
            return column[0]

        # rows
        row = board[i*4: 4*i+4]
        if (row[0] and row.count(row[0]) == 4):
            return row[0]

    # check diagonals
    diag1 = [board[i] for i in [0, 5, 10, 15]]
    diag2 = [board[i] for i in [3, 6, 9, 12]]

    if (diag1[0] and diag1.count(diag1[0]) == 4):
        return diag1[0]
    if (diag2[0] and diag2.count(diag2[0]) == 4):
        return diag2[0]

    # if still spots
    if 0 in board:
        return None

    return 0


def get_utility_3d(board: Tuple[Tuple[Optional[int], ...], ...]
                   ) -> Optional[int]:

    b1, b2, b3, b4 = board
    winners = [1, -1]

    # slicing board in x,y,z dirs
    for i in range(4):

        # xy plane
        sliceboard = board[i]
        result = get_utility_2d(sliceboard)
        if result in winners:
            return result

        # yz plane
        sliceboard = b1[i*4: 4*i+4] + b2[i*4: 4*i+4] + \
            b3[i*4: 4*i+4] + b4[i*4: 4*i+4]
        result = get_utility_2d(sliceboard)
        if result in winners:
            return result

        # xz plane
        sliceboard = b1[i*4: 4*i+4] + b2[i*4: 4*i+4] + \
            b3[i*4: 4*i+4] + b4[i*4: 4*i+4]
        result = get_utility_2d(sliceboard)
        if result in winners:
            return result

    # test the remaining diagonals

    diag1 = board[0][0], board[1][5], board[2][10], board[3][15]
    diag2 = board[3][0], board[2][5], board[1][10], board[0][15]
    diag3 = board[0][3], board[1][6], board[2][9], board[3][12]
    diag4 = board[3][3], board[2][6], board[1][9], board[0][12]

    for diag in [diag1, diag2, diag3, diag4]:
        if (diag[0] and diag.count(diag[0]) == 4):
            return diag[0]

    # test if still open spaces
    for b in board:
        if 0 in b:
            return None

    return 0


def unpack_board(board: Tuple[Tuple[Optional[int], ...], ...]
                 ) -> List[Optional[int]]:
    b1, b2, b3, b4 = board
    return list(b1 + b2 + b3 + b4)


def repack_board(board: List[Optional[int]]
                 ) -> Tuple[Tuple[Optional[int], ...], ...]:
    return (tuple(board[0:16]),
            tuple(board[16:32]),
            tuple(board[32:48]),
            tuple(board[48:64]))


class Node:
    def __init__(self, board, player, parent=None, move_played=None):
        self.board = board
        self.children = []
        self.parent = parent
        self.move_played = move_played

        self.total_tries = 0
        self.num_wins = 0

        self.player = player


def get_next_move_indicies(board: Tuple[Tuple[Optional[int], ...], ...]
                           ) -> List[int]:
    unpacked_b = unpack_board(board)
    indicies = []

    while 0 in unpacked_b:
        free_spot = unpacked_b.index(0)
        indicies.append(free_spot)
        unpacked_b[free_spot] = 1

    return indicies


# given the indicie, return a board with the correct player now in that spot
def make_move(board: Tuple[Tuple[Optional[int], ...], ...],
              player: int, move_index: int
              ) -> Tuple[Tuple[Optional[int], ...], ...]:
    unpacked_b = unpack_board(board)
    unpacked_b[move_index] = player
    return repack_board(unpacked_b)


def backprop(current_node: Node, result: int) -> None:

    # recursively update the results until get to parent
    while current_node.parent:

        current_node.total_tries += 1

        if result == current_node.player:
            current_node.num_wins += 1
        elif result == 0:
            current_node.num_wins += 0.5

        current_node = current_node.parent

    # updating the root
    current_node.total_tries += 1


def rollout(current_node: Node) -> int:

    # choose random (valid) moves until we get to a terminal state
    current_board = current_node.board
    result = get_utility_3d(current_board)
    player = current_node.player

    turn = True

    while result is None:

        if not turn:
            player = player * -1

        next_move_indicies = get_next_move_indicies(current_board)
        current_board = make_move(
            current_board, player, random.choice(next_move_indicies))
        result = get_utility_3d(current_board)
        turn = not turn

    return result


def calculate_ucb(node: Node) -> float:
    n = node.total_tries
    if n == 0:
        return math.inf

    w = node.num_wins
    c = math.sqrt(4)
    bigN = node.parent.total_tries

    return w/n + c * math.sqrt(math.log(bigN) / n)


def generate_children(node: Node) -> None:

    next_move_indicies = get_next_move_indicies(node.board)

    for move_index in next_move_indicies:
        new_board = make_move(node.board, node.player * -1, move_index)
        child = Node(new_board, node.player * -1, node, move_index)
        node.children.append(child)


def get_best_move_currently(root: Node) -> int:

    # find the best ratio of wins to total tries
    ratios = [child.num_wins / child.total_tries for child in root.children]
    best_ratio_index = ratios.index(max(ratios))

    return root.children[best_ratio_index].move_played


def find_best_move(board: Tuple[Tuple[Optional[int], ...], ...],
                   player: int, best_move: List[int], table: Dict
                   ) -> Optional[int]:

    num_rollouts = 40
    num_steps = 1000

    # best_move[0] = 0

    # create root node
    root = Node(board, player * -1)

    # create child nodes for all the next possible moves
    generate_children(root)

    # rollouts and backprops for each child node to get some initial statistics
    for child in root.children:
        for _ in range(num_rollouts):
            res = rollout(child)
            backprop(child, res)

    for _ in range(num_steps):

        # select successive child nodes (by ucb) until a leaf node L is reached
        current = root
        while current.children:

            # figure out the child with best ucb and choose it
            highest_ucb = 0
            best_child = None
            for child in current.children:
                ucb = calculate_ucb(child)
                if ucb > highest_ucb:
                    highest_ucb = ucb
                    best_child = child
            current = best_child

        # if the leaf ends the game, don't generate children
        utility = get_utility_3d(current.board)

        # check if the leaf node L has been visited yet (if total_tries == 0)
        if current.total_tries == 0:
            res = rollout(current)
            backprop(current, res)

        # if it has been visited, expand and then randomly pick
        # and also this will never happen until ALL the child have been
        # visited at least once, cause if it hasn't been visited it
        # will get chosen by highest ucb
        elif utility is None:
            generate_children(current)
            random_child = random.choice(current.children)
            res = rollout(random_child)
            backprop(random_child, res)

        best_move[0] = get_best_move_currently(root)

    return best_move[0]
