# -*- coding: utf-8 -*-

import scrapy
from scraping.items import CoursesItem
from scraping.items import CoursePageItem
from scraping.items import DataItem


class CoursesSpider(scrapy.Spider):
    #Overridden params
    name = "courses"
    allowed_domains = ["courses.cs.ut.ee"]
    start_urls = ["https://courses.cs.ut.ee/courses/old"]

    #Custom params
    filter_url = "https://courses.cs.ut.ee"
    allowed_semesters = []
    allowed_extensions = ('.pdf', '.pptx', '.doc')

    def __init__(self, semesters='', *args, **kwargs):
        """ Expected format '2016F,2014S' - i.e 2016 fall semester and 2014 spring semester
            The 'semesters' parameter is passed via -a argument """

        super(CoursesSpider, self).__init__(*args, **kwargs)
        self.allowed_semesters = self.__parse_semesters(semesters)

    def parse(self, response):
        for sel in response.xpath("//table[@class=\"table previous-years\"]/tr"):
            for it in sel.xpath(".//a"):
                link = it.xpath("@href").extract()[0]

                # Choose only wanted semesters
                for x in self.allowed_semesters:
                    if x[0] in link and x[1] in link:
                        request = scrapy.Request(self.filter_url + ''.join(link), callback=self.parse_courses)
                        request.meta['year'] = x[0]
                        request.meta['semester'] = x[1]
                        yield request

    def parse_courses(self, response):
        for sel in response.xpath("//ul[@class=\"course-list\"]").xpath(".//li"):
            item = CoursesItem()
            item["title"] = sel.xpath("a/text()").extract()
            item["link"] = sel.xpath("a/@href").extract()
            item["code"] = sel.xpath(".//span/text()").extract()
            yield item
            request = scrapy.Request(self.filter_url + ''.join(item['link']), callback=self.parse_navbar)
            request.meta['course'] = item
            request.meta['year'] = response.meta['year']
            request.meta['semester'] = response.meta['semester']
            yield request

    def parse_navbar(self, response):
        for sel in response.xpath("//nav[@class=\"sidebar\"]").xpath(".//a"):
            t_link = ''.join(sel.xpath("@href").extract())
            # only follow links in navbar that are inside allowed domain
            if t_link.find(self.filter_url) > -1:
                item = CoursePageItem()
                item["title"] = sel.xpath("text()").extract()
                item["link"] = sel.xpath("@href").extract()
                # yield item
                request = scrapy.Request(''.join(item['link']), callback=self.parse_article)
                request.meta['course'] = response.meta['course']
                request.meta['year'] = response.meta['year']
                request.meta['semester'] = response.meta['semester']
                yield request

    def parse_article(self, response):
        try:
            for sel in response.xpath("//article[@class=\"content\"]"):
                item = DataItem()
                item['link'] = response.url
                item['path'] = ''
                item['content'] = sel.extract()
                course = response.meta['course']
                item['course_code'] = course['code']
                item['year'] = response.meta['year']
                item['semester'] = response.meta['semester']
                yield item
        except AttributeError:
            pass

        for sel in response.xpath("//a"):
            t_link = ''.join(sel.xpath("@href").extract())
            if self.__is_valid_url(t_link):
                item = DataItem()
                item['title'] = sel.xpath("text()").extract()
                item['link'] = sel.xpath("@href").extract()
                item['path'] = '/' + ''.join(response.url).replace(self.filter_url, '')
                course = response.meta['course']
                item['course_code'] = course['code']
                item['content'] = ''
                item['year'] = response.meta['year']
                item['semester'] = response.meta['semester']
                yield item

    @staticmethod
    def __parse_semesters(semesters_str):
        semesters = []
        for sem in semesters_str.split(","):
            if len(sem) != 5:
                print "Invalid parameter length, expected 5, actual: {}".format(len(sem))
                continue

            season = sem[-1].upper()
            if season == 'F':
                season = 'fall'
            elif season == 'S':
                season = "spring"
            else:
                print "Invalid semester, expected either F or S, actual: {}".format(sem[-1])
                continue

            semesters.append((sem[:4], season))

        return list(set(semesters))

    def __is_valid_url(self, url):
        return url.endswith(self.allowed_extensions) and url.find("action=upload") == -1
