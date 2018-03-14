# -*- coding: utf-8 -*-

import scrapy, logging

from scraping.items import CoursesItem
from scraping.items import DataItem
from scraping.settings import ALLOWED_EXTENSIONS
from utils.SemesterUtils import parse_semesters
from utils.ConfigReader import Config


class Ois7Spider(scrapy.Spider):
    #Overridden params
    name = "ois7"
    allowed_domains = []
    start_urls = []

    #Custom params
    allowed_semesters = []

    def __init__(self, semesters='', *args, **kwargs):
        """ Expected format '2016F,2014S' - i.e 2016 fall semester and 2014 spring semester
            The 'semesters' parameter is passed via -a argument """

        super(Ois7Spider, self).__init__(*args, **kwargs)
        cfg = Config()
        course_info = cfg.get_ois7_info()
        self.allowed_domains = course_info.get("allowed_domains")
        self.start_urls = course_info.get("start_urls")

        # Commandline parameters override file parameters
        if semesters:
            self.allowed_semesters = parse_semesters(semesters)
        else:
            self.allowed_semesters = cfg.get_allowed_semesters()

    def parse(self, response):
        filter_url = self.__determine_filter_url(response)

        for sel in response.css("a"):
            hrefsplit = sel.css("a::text").extract_first().split(' ', 1)

            item = CoursesItem()
            item["title"] = hrefsplit[1]
            item["link"] = sel.css("a::attr(href)").extract_first()
            item["code"] = hrefsplit[0]
            item["year"] = '2017'
            item["semester"] = 'fall'
            yield item

            meta = {}
            meta["course"] = item
            meta["filter"] = filter_url

            yield response.follow(sel.css("a::attr(href)").extract_first(), callback=self.parse_others, meta=meta)

    def parse_others(self, response):
        yield self.__create_data_item(response.url, response.body, response)

    def __determine_filter_url(self, response):
        filter_url = "https://" if "https:" in response.url else "http://"
        for domain in self.allowed_domains:
            if domain in response.url:
                filter_url += domain
                break

        return filter_url

    @staticmethod
    def __create_data_item(link, content, response):
        course = response.meta['course']

        item = DataItem()
        item['link'] = link
        item['path'] = ''.join(response.url).replace(response.meta['filter'], '') if not content else ''
        item['content'] = content
        item['course_code'] = course['code']
        item['year'] = '2017'
        item['semester'] = 'fall'

        return item

    @staticmethod
    def __is_valid_url(url):
        return url.endswith(ALLOWED_EXTENSIONS) and url.find("action=upload") == -1
