#!/usr/bin/python3

import os
import requests
import argparse
from datetime import datetime, timedelta, timezone
import sys
import pytz


def create_parser():
    def _date(value):
        try:
            return datetime.strptime(value, "%d/%m/%Y-%H:%M")
        except Exception:
            raise ValueError

    parser = argparse.ArgumentParser(
        description="Нахождение расстояния и времени между адресами, "
                    "используя Google Maps Distance Matrix API")
    parser.add_argument("-b", "--begin", help="Адреса начальных точек пути "
                                              ",разделённые запятыми",
                        nargs="+", required=True)
    parser.add_argument("-e", "--end", help="Адреса конечных точек пути "
                                            ",разделённые запятыми",
                        nargs="+", required=True)
    parser.add_argument("-r", "--traffic_model",
                        choices=["optimistic", "pessimistic", "best_guess"],
                        help='указывает предположения, используемые при '
                             'расчете времени в пути, '
                             'best_guess (по умолчанию) – означает, что '
                             'возвращаемое значение '
                             'должно содержать наилучшую оценку '
                             'ожидаемого времени пути с учетом имеющейся '
                             'статистической информации '
                             'по движению и текущей дорожной обстановки.'
                             'pessimistic - время больше среднего значения, '
                             'optimistic - меньше')
    parser.add_argument("-m", "--mode",
                        choices=["driving", "walking", "bicycling", "transit"],
                        help="используемый способ передвижения, "
                             "driving (по умолчанию) – указывает расчет "
                             "расстояния по дорожной сети. "
                             "walking – запрос расчета расстояния для "
                             "передвижения пешком по пешеходным дорожкам "
                             "и тротуарам (где это возможно)."
                             "bicycling – запрос расчета расстояния для "
                             "передвижения на велосипеде по велосипедным "
                             "дорожкам и предпочитаемым улицам. "
                             "transit – запрос расчета расстояния для "
                             "передвижения на общественном транспорте")
    parser.add_argument("-t", "--departure_time",
                        help="время отправления, в формате yyyy/mm/dd-hh:mm, "
                             "по умолчанию - текущее время",
                        type=_date, default=datetime.now())
    parser = parser.parse_args()
    if parser.traffic_model:
        parser.mode = "driving"
    return parser


if __name__ == '__main__':
    parser = create_parser()
    start_time = datetime(1970, 1, 1)
    parser.departure_time -= datetime.now(timezone.utc).astimezone().utcoffset()
    if not os.path.exists("keys"):
        print("Нет файла с ключами 'keys'", file=sys.stderr)
        sys.exit(1)
    with open("keys") as keys:
        for key in keys:
            url = ("https://maps.googleapis.com/maps/api/distancematrix/json?"
                   "origins=+ON%s&destinations=%s+ON&language=ru-RU&key=%s"
                   "&departure_time=%s" % (
                       "+".join(parser.begin).replace(",", "+ON|"),
                       "+".join(parser.end).replace(",", "+ON|"),
                       key.strip(),
                       int((parser.departure_time -
                            start_time).total_seconds())))
            if parser.mode:
                url += "&mode=%s" % parser.mode
            time_accounting = "duration"
            if parser.traffic_model:
                url += "&traffic_model=%s" % parser.traffic_model
                time_accounting = "duration_in_traffic"
            req = requests.get(url, timeout=5)
            answer = req.json()
            if "error_message" in answer:
                print(answer["error_message"], file=sys.stderr)
                continue
            if answer["status"] != "OK":
                print(answer["status"], sys.stderr)
                continue
            for i in range(len(answer["origin_addresses"])):
                for j in range(len(answer["destination_addresses"])):
                    print("—" * 50)
                    print("От: %s(%s)\nДо: %s(%s)\n" % (
                        (" ".join(parser.begin).split(","))[i],
                        answer["origin_addresses"][i],
                        (" ".join(parser.end).split(","))[j],
                        answer["destination_addresses"][j]))
                    if answer["rows"][i]["elements"][j]["status"] != "OK":
                        print(answer["rows"][i]["elements"][j]["status"],
                              file=sys.stderr)
                        continue
                    print("Расстояние: %s\nВремя: %s\n" % (
                        answer["rows"][i]["elements"][j]["distance"]["text"],
                        answer["rows"][i]["elements"][j][
                            time_accounting]["text"]))
            print("—" * 50)
            req.close()
            sys.exit(0)

