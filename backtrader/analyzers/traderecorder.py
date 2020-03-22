#######################################
# Code: Rich O'Regan  (London) Nov 2017
#######################################

import math
import numpy as np
import pandas as pd

from backtrader import Analyzer
from backtrader.utils import AutoOrderedDict, AutoDict


class TradeRecorder(Analyzer):
    '''

    Summary:

        TradeRecorder enables user to save all trades produced by strategy and
        also the corresponding equity curve.

        NOTE: to record trades, the Trade object needs to be modified because
        'exit_price' and 'exit_date' do not exist in the public Backtrader
        version. So you need to use the hacked 'trade.py' modification by
        Richard O'Regan that includes these extra attributes.

        [Or you can add them yourself in the Trade.update() code.
        At very end of the method add;

                self.entry_price = self.price
                self.exit_price = price

        This code only works for simple trades with one exit and one entry.
        Assume one unit traded, not tested with different trade sizes.]


        TRADE RECORDING MODE
        After strategy has ran, if mode = "trade" or "trade+equity", a DataFrame
        of open trades and a DataFrame of closed trades can be accessed via;

                self.rets.openTrades
                self.rets.closedTrades

        The above information can be used to e.g. visulise all trades produced
        with a strategy by plotting them on top of the market data chart.
        The trades can be visually checked to ensure the strategy has been coded
        correctly.


        EQUITY RECORDING MODE
        If mode = "equity" or "trade+equity", a DataFrame representing the
        equity curve can be accessed via;

            self.rets.equityCurve

        The above information can be used to visulise the equity curve for a
        strategy and it's particular parameters.

        USE
        It is advised to set the parameter to record only the data you need.
        This will save space in memory (and storage if you write to disk).


    Params:

           - ``mode``: (default: ``trade+equity``)

           - options are ``trades``, ``equity`` or ``trades+equity``

            If ``trades`` option, record all data related to trade enough to
            be able to plot on a chart the exact entry & exit date and price.

            Data recorded:

                'entry_price' from Trade.entry_price
                'entry_date' from Trade.open_datetime()
                *'exit_price' from Trade.exit_price
                *'exit_date' from Trade.close_datetime()
                'pnl' from Trade.pnl
                'pnlcomm' from Trade.pnlcomm
                'tradeid' from Trade.tradeid


            If ``equity`` option record enough data to be able to plot an equity curve.

            Data recorded:

                'exit_date' from Trade.close_datetime()
                'equity' from cumulative sum of Trade.pnlcomm

                NOTE: The actual account equity is *NOT* recorded,
                instead cumulative equity from each trade. Always starts from 0.


            If ``trades+equity`` option, record all of data mentioned above.


    Methods:

      - get_analysis

        Returns threes DataFrame, one each for;
                Open trades     ---> Records trades entries and exits.
                Closed trades   ---> Records trades entries and exits.
                Equity curve    ---> Records cumulative pnl.


    [This 'traderecorder.py' was coded by Richard O'Regan (London) Nov 2017]
    '''


    # Declare parameters user can pass to this Analyzer..
    params = (
             ('mode', 'trades+equity' ),
             )


    def create_analysis(self):
        # Keep dict of trades based on tradeid.
        # Note: must be a unique tradeid defined for each trade else will
        # get overwritten.
        self.rets = AutoOrderedDict()
        self.rets.openTrades = []   # List of all open trades..
        self.rets.closedTrades = [] # List of all closed trades..
        self.rets.equityCurve = [] # List of dictonary

        # Hidden from user, destroyed at end, useful to track trades.
        self._tradeDict = {}    # Temp store Trade objects..
        self._cumulativeEquity = None   # Keep track of our equity..

        # Check user parameters are valid - if not raise Exception.
        if self.p.mode not in ['trades', 'equity', 'trades+equity']:
            raise Exception("TradeRecorder Analyzer must have parameter " +
                "'mode' set to either 'trades', 'equity' or 'trades+equity'." +
                f"\nInstead you have set it to '{self.p.mode}'.")


    def notify_trade(self, trade):
        # Add Trade object to our trade dict which records all trades..
        # Great thing is, don't care if open or closed, if an open trade
        # becomes closed, it is simply rewritten (because same tradeid/key).
        # Note: must be a unique tradeid for each trade else overwritten.
        self._tradeDict[trade.tradeid]=trade


    def stop(self):
        # Create our output list of closed and open trades we have tracked..
        for n in self._tradeDict:

            trade = self._tradeDict[n]   # Get value (ie Trade object)

            # Create DataFrame of essential attributes of Trade object..
            # Note: we dont save Trade objects because they are inefficient and
            # each Trade object appears to save whole market data (retarded)..

            # Common information to store for both open and closed trades..
            # Set up basic dataframe row used for both open & closed trades.
            # We later append columns to this for closed trades..

            if hasattr(trade,'R'):
                _trade=pd.DataFrame([
                    {'entry_price':trade.entry_price,
                    'entry_date':trade.open_datetime(),
                    'pnl':trade.pnl,
                    'pnlcomm':trade.pnlcomm,
                    'is_long':trade.long,
                    'R_stop':trade.R,                # Append R-stop if it exists..
                    'tradeid':trade.tradeid}])

            else:
                _trade=pd.DataFrame([
                    {'entry_price':trade.entry_price,
                    'entry_date':trade.open_datetime(),
                    'pnl':trade.pnl,
                    'pnlcomm':trade.pnlcomm,
                    'is_long':trade.long,
                    'tradeid':trade.tradeid}])

            # Check if trade open or closed..
            if trade.isopen and self.p.mode in ['trade','trades+equity']:
                # This trade is still open..
                # Limited to what data we have because trade not closed out
                # e.g. no exit date and no equity curve change.
                self.rets.openTrades.append(_trade)  # Save open trade dict

            else:
                # Trade closed.
                # Calc & store equity if required..
                #if self.p.mode in ['equity','trades+equity']:
                #    _equity = self.calc_equity(trade)
                #    self.rets.equityCurve.append(_equity)

                # Calc & store trades if required..
                if self.p.mode in ['trades','trades+equity']:
                    # Need to use the hacked Trade objects that included
                    # exit price and date..
                    # If attributes don't exist, raise an error..
                    try:
                        _trade['exit_date'] = trade.close_datetime()
                        _trade['exit_price'] = trade.exit_price
                    except AttributeError as e:
                        print(e,'\nThe Trade object received by this ' +
                            'TradeRecorder Analyzer is missing extra ' +
                            'attributes\nnot included in the public ' +
                            'Backtrader version. ' +
                            'To use this Analyzer, you need to ' +
                            'hack\n"trade.py" to add in two extra ' +
                            ' attributes. See Rich O\'Regan for details.')
                        raise

                    self.rets.closedTrades.append(_trade)


        # Append single DataFrame to a list, then concatenate list to one big
        # DataFrame because more efficient than lots of appending to DF..
        o=self.rets
        if self.p.mode in ['trades', 'trades+equity']:
            o.closedTrades = (pd.concat(o.closedTrades).reset_index(drop=True)
                             if o.closedTrades!=[] else None)
            o.openTrades = (pd.concat(o.openTrades).reset_index(drop=True)
                           if o.openTrades!=[] else None)
        else:
            o.closedTrades = o.openTrades = None    # Trades not required..

        #if self.p.mode in ['equity', 'trades+equity']:
        #    o.equityCurve = (pd.concat(o.equityCurve).reset_index(drop=True)
        #                     if o.equityCurve!=[] else None)
        #else:
        #    o.equityCurve = None    # Equity not required by user..

        # Calculate equity curve DataFrame from Trade DataFrame..
        # NOTE: we need to sort dates and calc cumulative equity using
        # the closing date (instead of opening date)..
        if self.p.mode in ['equity', 'trades+equity']:
            _df = o.closedTrades[['exit_date','pnlcomm']].copy()
            _df.sort_values(['exit_date'],ascending=True, inplace=True)
            _df = _df.reset_index(drop=True)
            _df['pnlcomm']=_df.pnlcomm.cumsum()  # Calc cumulative equity..
            _df.columns=['date','equity']  # Rename the two columns..
            o.equityCurve = _df
        else:
            o.equityCurve = None    # Equity not required by user..


        # 'Kill' internal list of Trade objects by setting to 'None'.
        # Inefficient if kept. We don't want list of bloated Trade objects to be
        # saved. (BackTrader Cerebro optimisation feature automatically saves
        # this Analyzer and all attributes).
        self._tradeDict = None
        self.rets._close()    # Check if we need this..


    def calc_equity(self, trade):
        # Calculate the equity change for each closed trade.
        # Record date & cumulative pnl, so that an equity curve can be plotted.

        # Mostly straight forward, keep a track of the current pnl , which
        # always starts from 0 (NOT interested in account equity e.g. $10,000).

        # Curve must start from zero, which should be start of data.
        # We don't know the start of the market data (though it could be found
        # with more code), so;
        # The very first value, use the *ENTRY* date of first trade and value 0.
        # For all other closed trades use the *EXIT* date and the value is found
        # by adding latest pnl to cumulative equity.

        # OUTPUT:
        # A DataFrame of a single row returned (or two rows if first trade).

        # IMPLEMENTATION:
        # The very first trade identified by _cumulativeEquity = None
        # Then two rows are returned;
        # i.e.
        # TRADE1
        # ROW1: entry_date of TRADE1, 0
        #  _cumulativeEquity = 0 + pnl of TRADE1
        # ROW2: exit_date of TRADE1, _cumulativeEquity

        # TRADE2
        # _cumulativeEquity = _cumulativeEquity + pnl of TRADE2
        # ROW3: exit_date of TRADE2, _cumulativeEquity

        if self._cumulativeEquity == None:
            # First time, initialise. Generate two rows..
            self._cumulativeEquity = trade.pnlcomm
            _trade = pd.DataFrame([
                {'date':trade.open_datetime(),
                 'equity':0},
                {'date':trade.close_datetime(),
                  'equity':self._cumulativeEquity}])

        else:
            # Not first time, so add latest value of pnl to current equity..
            self._cumulativeEquity += trade.pnlcomm
            _trade = pd.DataFrame([
                {'date':trade.close_datetime(),
                  'equity':self._cumulativeEquity}])

        return _trade


    def print(self, *args, **kwargs):
        '''
        Overide print method to display length of list rather than contents.
        (We don't want e.g. 1000 trades to be displayed.)
        '''
        print('TradeRecorder:')
        print(f'  - openTrades = list of length {len(self.rets.openTrades)}')
        print(f'  - closedTrades = list of length {len(self.rets.closedTrades)}')
