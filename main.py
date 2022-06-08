from spiders import SpiderFactory


if __name__ == "__main__":
    spider = SpiderFactory().gen_worker()
    spider.run()