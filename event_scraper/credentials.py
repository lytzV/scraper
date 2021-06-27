EMAIL = ""
PSWD = ""

prefix1 = "/html/body//div[contains(concat(' ',normalize-space(@class)),' d2edcug')][contains(concat(' ', normalize-space(@class), ' '),' cbu4d94t ')][contains(concat(' ',normalize-space(@class)),' j83agx')][contains(concat(' ', normalize-space(@class), ' '),' bp9cbjyn ')]/div/iframe//div[@id='upcoming_events_card']/div//div[@class='_24er']/table/tbody/tr/"
xpaths1 = {
    "title":prefix1+'td[2]/div/div[1]/a/span/text()',
    "t1":prefix1+'td[2]/div/div[2]/span[1]/text()',
    "t2-month":prefix1+'td[1]/span/span[1]/text()',
    "t2-date":prefix1+'td[1]/span/span[2]/text()',
    "loc":prefix1+'td[3]/div/div/a/text()',
}


prefix2 = "//div[@id='upcoming_events_card']/div//div[@class='_24er']/table/tbody/tr/"
xpaths2 = {
    "title":prefix2+'td[2]/div/div[1]/a/span',
    "t1":prefix2+'td[2]/div/div[2]/span[1]',
    "t2-month":prefix2+'td[1]/span/span[1]',
    "t2-date":prefix2+'td[1]/span/span[2]',
    "loc":prefix2+'td[3]/div'
}

