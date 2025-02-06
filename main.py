import copy

import requests
from fastapi import FastAPI
import fastapi
from pydantic import BaseModel
import uvicorn
import os
import signal
import logging
import numpy as np

"""
By Todd Dole, Revision 1.1
Written for Hardin-Simmons CSCI-4332 Artificial Intelligence
Revision History
1.0 - API setup
1.1 - Very basic test player
"""

# TODO - Change the PORT and USER_NAME Values before running
DEBUG = True
PORT = 10201
USER_NAME = "bkd2008"
# TODO - change your method of saving information from the very rudimentary method here
hand = [] # list of cards in our hand
discard = [] # list of cards organized as a stack
hand_matrix = np.zeros((4, 13))
card_matrix = np.zeros((4, 13)) #{0: unknown, 1: my hand, 2: opponent hand, 3: discard, 4: stock}
num_of_each = []
diamonds = hand_matrix[0]
hearts = hand_matrix[1]
spades = hand_matrix[2]
clubs = hand_matrix[3]
to_numeric = {
    'T': 10,
    'J': 11,
    'Q': 12,
    'K': 13,
    'A': 14,
    'D': 0,
    'H': 1,
    'S': 2,
    'C': 3
}
from_numeric = {num: letter for letter, num in to_numeric.items()}

hand_length = 10
drew_discard = False

# set up the FastAPI application
app = FastAPI()


def sort_by_value(hand):
    hand_list = []
    for i in range(10):
        for j in range(4):
            if (hand_matrix[i][j] == 1):
                card = (int(i+2), from_numeric[j])
    for i in range(10, 15):
        for j in range(4):
            if (hand_matrix[i][j] == 1):
                card = (i, from_numeric[j])

    for card in list(hand):
        # print(card)
        hand_list.append([str(card)[0], str(card)[1]])  #[val, suit]

    for card in hand_list:
        if (card[0] == 'T'):
            card[0] = '10'
        elif (card[0] == 'J'):
            card[0] = '11'
        elif (card[0] == 'Q'):
            card[0] = '12'
        elif (card[0] == 'K'):
            card[0] = '13'
        elif (card[0] == 'A'):
            card[0] = '14'


    hand_list.sort(key=lambda card: int(card[0]))   #Got this line from chatgpt
    # for card in hand_list:
    #     hand_list[hand_list.index(card)] = str(card[0]) + str(card[1])
    return hand_list

def to_matrix(hand):
    for card in hand:
        val = card[0]
        suit = card[1]
        if (not val.isnumeric()):
            val = to_numeric[card[0]]
        suit = to_numeric[card[1]]

        card = (int(val), suit)
        logging.info(card)

        hand_matrix[int(suit)][int(val)-2] = 1

    logging.info(hand_matrix)




# set up the API endpoints
@app.get("/")
async def root():
    ''' Root API simply confirms API is up and running.'''
    return {"status": "Running"}

# data class used to receive data from API POST
class GameInfo(BaseModel):
    game_id: str
    opponent: str
    hand: str


# data class used to receive data from API POST
class UpdateInfo(BaseModel):
    game_id: str
    event: str


# data class used to receive data from API POST
class HandInfo(BaseModel):
    hand: str


@app.post("/start-2p-game/")
async def start_game(game_info: GameInfo):
    ''' Game Server calls this endpoint to inform player a new game is starting. '''
    # TODO - Your code here - replace the lines below

    hand = game_info.hand.split(" ")
    hand_matrix = to_matrix(copy.deepcopy(hand))

    global discard

    hand_sorted_val = sort_by_value(hand)
    hand.sort() #needs to be on a separate line else hand is None, idk why
    global num_of_each
    for i in range(13):
        num_of_each.append(0)
    for card in hand_sorted_val:
        num_of_each[int(card[0])-2] += 1
    logging.info("2p game started, hand is "+str(hand))
    logging.info("Hand sorted by value is: " + str(hand_sorted_val))
    logging.info("Number of each value is: " + str(num_of_each))
    return {"status": "OK"}


@app.post("/start-2p-hand/")
async def start_hand(hand_info: HandInfo):
    ''' Game Server calls this endpoint to inform player a new hand is starting, continuing the previous game. '''
    # TODO - Your code here
    global hand
    hand = hand_info.hand.split(" ")
    hand_matrix = to_matrix(copy.deepcopy(hand))

    global discard
    hand = hand_info.hand.split(" ").sort()
    global num_of_each
    for i in range(0, 13):
        num_of_each.append(0)
    logging.info("2p hand started, hand is " + str(hand))
    logging.info("Hand sorted by value is: " + str(sort_by_value(hand)))
    return {"status": "OK"}


def process_events(event_text):
    ''' Shared function to process event text from various API endpoints '''
    # TODO - Your code here. Everything from here to end of function
    global hand
    global discard
    for event_line in event_text.splitlines():

        if ((USER_NAME + " draws") in event_line or (USER_NAME + " takes") in event_line):
            print("In draw, hand is "+str(hand))
            hand.append(event_line.split(" ")[-1])
            hand.sort()
            print("Hand is now "+str(hand))
            # logging.info("Drew a "+event_line.split(" ")[-1]+", hand is now: "+str(hand))
        if ("discards" in event_line):  # add a card to discard pile
            discard.insert(0, event_line.split(" ")[-1])
        if ("takes" in event_line): # remove a card from discard pile
            discard.pop(0)


@app.post("/update-2p-game/")
async def update_2p_game(update_info: UpdateInfo):
    '''
        Game Server calls this endpoint to update player on game status and other players' moves.
        Typically only called at the end of game.
    '''
    # TODO - Your code here - update this section if you want
    process_events(update_info.event)
    return {"status": "OK"}


@app.post("/draw/")
async def draw(update_info: UpdateInfo):
    ''' Game Server calls this endpoint to start player's turn with draw from discard pile or draw pile.'''
    # TODO - Your code here - everything from here to end of function
    process_events(update_info.event)
    if len(discard)<1: # If the discard pile is empty, draw from stock
        return {"play": "draw stock"}
    if any(discard[0][0] in s for s in hand): # if our hand contains a matching card, take it
        return {"play": "draw discard"}
    return {"play": "draw stock"} # Otherwise, draw from stock


@app.post("/lay-down/")
async def lay_down(update_info: UpdateInfo):
    ''' Game Server calls this endpoint to conclude player's turn with melding and/or discard.'''
    # TODO - Your code here - everything from here to end of function
    global hand
    global discard
    process_events(update_info.event)
    of_a_kind_count = [0, 0, 0, 0] # how many 1 of a kind, 2 of a kind, etc in our hand
    last_val = hand[0][0]
    count = 0
    for card in hand[1:]:
        cur_val = card[0]
        if cur_val == last_val:
            count+=1
        else:
            of_a_kind_count[count] += 1
            count=0
        last_val = cur_val
    if (count!=0): of_a_kind_count[count]+=1 # Need to get the last card fully processed if it is a match to the previous
    if (of_a_kind_count[0]+of_a_kind_count[1]) > 1:
        # Too many unmeldable cards, need to discard

        # If we have a 1 of a kind, discard the highest
        if (of_a_kind_count[0]>0):
            for i in range(len(hand)-1,-1, -1):
                if (i==0):
                    # logging.info("Discarding "+hand[0])
                    return {"play":"discard "+hand.pop(0)}
                if hand[i][0] != hand[i-1][0]:
                    # logging.info("Discarding "+hand[i])
                    return {"play":"discard "+hand.pop(i)}

        # discard the highest 2 of a kind
            i=len(hand)-1
            while (i>0):
                if (i==1):
                    # logging.info("Discarding "+hand[1])
                    return {"play":"discard "+hand.pop(1)}
                if hand[i][0] != hand[i-2][0]:
                    # logging.info("Discarding "+hand[i])
                    return {"play":"discard "+hand.pop(i)}
                while hand[i][0] == hand[i-1][0]: i-=1 #skip over meldable sets
                i-=1

    # We should be able to meld.

    # First, find the card we discard
    discard_string = ""
    print(of_a_kind_count)
    # TODO - Dole - Need to add edge case for last card being a one-of-a-kind
    if (of_a_kind_count[0] > 0):
        for i in range(len(hand)-1, -1, -1):
            if (i == 0):
                discard_string = " discard " + hand.pop(0)
                break
            if hand[i][0] != hand[i - 1][0]:
                discard_string = " discard " + hand.pop(i)
                break

    # generate our list of meld
    play_string = ""
    last_card = ""
    while (len(hand) > 0):
        card = hand.pop(0)
        if (str(card) != last_card):
            play_string += "meld "
        play_string += str(card) + " "
        last_card = str(card)

    # remove the extra space, and add in our discard if any
    play_string = play_string[:-1]
    play_string += discard_string

    logging.info("Playing: "+play_string)
    return {"play":play_string}


@app.get("/shutdown")
async def shutdown_API():
    ''' Game Server calls this endpoint to shut down the player's client after testing is completed.  Only used if DEBUG is True. '''
    os.kill(os.getpid(), signal.SIGTERM)
    logging.info("Player client shutting down...")
    return fastapi.Response(status_code=200, content='Server shutting down...')


''' Main code here - registers the player with the server via API call, and then launches the API to receive game information '''
if __name__ == "__main__":

    if (DEBUG):
        url = "http://127.0.0.1:16200/test"

        # TODO - Change logging.basicConfig if you want
        logging.basicConfig(level=logging.INFO)
    else:
        url = "http://127.0.0.1:16200/register"
        # TODO - Change logging.basicConfig if you want
        logging.basicConfig(level=logging.WARNING)

    payload = {
        "name": USER_NAME,
        "address": "127.0.0.1",
        "port": str(PORT)
    }

    try:
        # Call the URL to register client with the game server
        response = requests.post(url, json=payload)
    except Exception as e:
        print("Failed to connect to server.  Please contact Mr. Dole.")
        exit(1)

    if response.status_code == 200:
        print("Request succeeded.")
        print("Response:", response.json())  # or response.text
    else:
        print("Request failed with status:", response.status_code)
        print("Response:", response.text)
        exit(1)

    # run the client API using uvicorn
    uvicorn.run(app, host="127.0.0.1", port=PORT)

