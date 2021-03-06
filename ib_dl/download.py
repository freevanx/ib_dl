import datetime
import logging

import click
from ib_insync import IB, Stock, util

logger = logging.getLogger(__name__)

LOCAL_TZ = datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo


def _fetch_to_df(ib, symbol, duration, bar_size):
    logger.info(f'Downloading historical data of {symbol} for {duration} '
                f'with {bar_size} resolution')

    contract = Stock(symbol, exchange='SMART', currency='USD')
    bars = ib.reqHistoricalData(
        contract, endDateTime='', durationStr=duration,
        barSizeSetting=bar_size, whatToShow='TRADES', useRTH=True)

    df = util.df(bars)
    df.set_index('date', inplace=True)
    df.index = df.index.tz_localize(LOCAL_TZ).tz_convert('UTC')
    df['volume'] *= 100

    return df


def download(symbols, duration, bar_size, dest_dir, host, port, client_id):
    ib = IB()
    ib.connect(host, port, client_id)

    for symbol in symbols:
        df = _fetch_to_df(ib, symbol, duration, bar_size)
        df.drop(columns=['average', 'barCount'], inplace=True)

        start_date = df.first_valid_index().strftime("%Y%m%d")
        end_date = df.first_valid_index().strftime("%Y%m%d")

        filename = f'{dest_dir}/HC-{symbol}-1M-{start_date}-{end_date}-ib.csv'
        df.to_csv(filename)
        logger.info(f'Created file: {filename}')

        # Throttle to avoid 'Pacing violation'
        ib.sleep(11)


@click.command()
@click.argument('symbols', nargs=-1)
@click.option(
    '--duration',
    type=click.Choice(['1 D', '1 M', '3 M', '6 M', '1 Y']),
    help='Time duration to download data. Corresponds to durationString '
         'parameter of reqHistoricalData API call.'
)
@click.option(
    '--bar-size',
    type=click.Choice(['1 min', '1 day']),
    help='Data granularity. Corresponds to barSizeSetting parameter of'
         'reqHistoricalData API call.'
)
@click.option(
    '--dest-dir',
    default='.',
    type=click.Path(exists=True),
    help='Destination directory where the CSV will be stored'
)
@click.option(
    '--tws-uri',
    default='localhost:7492:995',
    help='URI to TWS with the following format: host:port:client_id'
)
@click.option(
    '--log-level',
    default='INFO',
    type=click.Choice(['INFO', 'DEBUG', 'WARNING', 'ERROR']),
    help='Set log level'
)
@click.pass_context
def main(ctx, symbols, duration, bar_size, dest_dir, tws_uri, log_level):
    if not duration:
        ctx.fail("must specify download duration with --duration")
    if not bar_size:
        ctx.fail("must specify data resolution with --bar-size")

    host = tws_uri.split(':')[0]
    port = int(tws_uri.split(':')[1])
    client_id = int(tws_uri.split(':')[2])

    logging.basicConfig(
        level=log_level,
        format='%(asctime)s [%(levelname)s] %(module)s %(message)s')

    download(symbols, duration, bar_size, dest_dir, host, port, client_id)


if __name__ == '__main__':
    main()
