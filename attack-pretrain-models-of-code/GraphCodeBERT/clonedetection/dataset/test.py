import  json
import random
sub_stitutes_path = "attack-pretrain-models-of-code\\GraphCodeBERT\\clonedetection\\dataset\\test_subs_0_500_alert.jsonl"
new_sub = []
with open(sub_stitutes_path, "r") as f:
    for line in f:
        js = json.loads(line.strip())
        rand_candi = random.randint(0,len(js["substitutes"]))
        try:
            candi = js["substitutes"][list(js["substitutes"].keys())[rand_candi]]
            poped_id = random.randint(0,len(candi))
            js["substitutes"][list(js["substitutes"].keys())[rand_candi]].pop(poped_id)
            new_sub.append(js)


        except:
            new_sub.append(js)
sub_stitutes_path_test = "attack-pretrain-models-of-code\\GraphCodeBERT\\clonedetection\\dataset\\test_subs_0_500_alert_test.jsonl"
with open(sub_stitutes_path_test, "w") as f:
    for line in new_sub:
        f.write(json.dumps(line)+'\n')