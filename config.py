import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    #local
    #SECRET_KEY = os.getenv("SECRET_KEY", "dev-key")
    #SQLALCHEMY_DATABASE_URI = ( "postgresql://postgres:123456@localhost:5432/dethi"   )
    
    #render
    SECRET_KEY = os.environ.get("SECRET_KEY","dev-secret" )
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    
    # SECRET_KEY = os.getenv("SECRET_KEY", "dev-key")
    #SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL","postgresql://postgres:123456@localhost:5432/dethi")
    

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    TURNSTILE_SITE_KEY = os.getenv("TURNSTILE_SITE_KEY")
    TURNSTILE_SECRET_KEY = os.getenv("TURNSTILE_SECRET_KEY")
    ALLOWED_OJ = ["codeforces.com", "atcoder.jp", "leetcode.com", "codechef.com", "hackerrank.com","cses.fi", "spoj.com", "uva.onlinejudge.org", "timus.onlinejudge.org", "kattis.com",
                  "codewars.com", "topcoder.com", "interviewbit.com", "geeksforgeeks.org", "hackerEarth.com", "projecteuler.net", "lightoj.com", "toph.co","oj.codedream.edu.vn",
                   "gymnasium.com", "oj.uz", "acmicpc.net", "yukicoder.me","lqdoj.com", "oj.vnoi.info","ojkhanhhoa.site","quangtrioj.edu.vn","ctoj.zapto.org","nhpoj.net","ctoj.net","oj.codejudge.edu.vn",
                   "oj.clue.edu.vn","oj.hncode.edu.vn","lkoj.edu.vn","claoj.edu.vn","ptnkoj.com","sqrtoj.edu.vn","hnoj.edu.vn","oj.chuyentin.pro","oj.cppro.vn"]