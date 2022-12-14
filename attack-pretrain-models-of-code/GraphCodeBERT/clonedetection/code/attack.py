'''For attacking GraphCodeBERT models'''
import sys
import os

sys.path.append('../../../')
sys.path.append('D:\\adv_ml\\attack-pretrain-models-of-code\python_parser')
sys.path.append("D:\\adv_ml\\attack-pretrain-models-of-code")
import csv
import copy
import pickle
import logging
import argparse
import warnings
import torch
import numpy as np
import json
import time
from model import Model
from utils import set_seed
from utils import Recorder
from run import TextDataset
from attacker import Attacker

from transformers import RobertaForMaskedLM
from transformers import (RobertaConfig, RobertaForSequenceClassification, RobertaTokenizer)
os.environ["CUDA_LAUNCH_BLOCKING"] = "1"
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
warnings.simplefilter(action='ignore') # Only report warning

MODEL_CLASSES = {
    'roberta': (RobertaConfig, RobertaForSequenceClassification, RobertaTokenizer)
}

logger = logging.getLogger(__name__)

def generate_used_file():
    sub_stitutes_path = "D:\\adv_ml\\test_subs_0_500.jsonl"

    # Fetch all available ids
    all_available_ids = []
    with open(sub_stitutes_path, "r") as f:
        for line in f:
            js = json.loads(line.strip())
            id1 = js["id1"]
            id2 = js["id2"]
            label = js["label"]
            all_available_ids.append((id1, id2, label))
    
    with open("test_subs_0_500.txt", "w") as f:
        for line in all_available_ids:
            f.write(line[0]+"\t"+line[1]+"\t"+str(line[2])+"\n")

            

    

def get_code_pairs(file_path):

    postfix=file_path.split('\\')[-1].split('.txt')[0]
    folder = '\\'.join(file_path.split('\\')[:-1]) # 得到文件目录
    code_pairs_file_path = os.path.join(folder, 'cached_{}.pkl'.format(postfix))
    with open(code_pairs_file_path, 'rb') as f:
        code_pairs = pickle.load(f)
    return code_pairs


def main():
    parser = argparse.ArgumentParser()
    #generate_used_file()
    ## Required parameters
    parser.add_argument("--train_data_file", default=None, type=str, required=False,
                        help="The input training data file (a text file).")
    parser.add_argument("--output_dir", default=None, type=str, required=False,
                        help="The output directory where the model predictions and checkpoints will be written.")

    ## Other parameters
    parser.add_argument("--eval_data_file", default=None, type=str,
                        help="An optional input evaluation data file to evaluate the perplexity on (a text file).")
    parser.add_argument("--test_data_file", default=None, type=str,
                        help="An optional input evaluation data file to evaluate the perplexity on (a text file).")
    parser.add_argument("--base_model", default=None, type=str,
                        help="Base Model")
    parser.add_argument("--model_type", default="bert", type=str,
                        help="The model architecture to be fine-tuned.")
    parser.add_argument("--model_name_or_path", default=None, type=str,
                        help="The model checkpoint for weights initialization.")
    parser.add_argument("--csv_store_path", default=None, type=str,
                        help="Base Model")
    parser.add_argument("--use_ga", action='store_true',
                        help="Whether to GA-Attack.")

    parser.add_argument("--config_name", default="", type=str,
                        help="Optional pretrained config name or path if not the same as model_name_or_path")
    parser.add_argument("--tokenizer_name", default="", type=str,
                        help="Optional pretrained tokenizer name or path if not the same as model_name_or_path")
    parser.add_argument("--cache_dir", default="", type=str,
                        help="Optional directory to store the pre-trained models downloaded from s3 (instread of the default one)")
    parser.add_argument("--code_length", default=256, type=int,
                        help="Optional Code input sequence length after tokenization.") 
    parser.add_argument("--data_flow_length", default=64, type=int,
                        help="Optional Data Flow input sequence length after tokenization.") 
    parser.add_argument("--do_train", action='store_true',
                        help="Whether to run training.")
    parser.add_argument("--do_eval", action='store_true',
                        help="Whether to run eval on the dev set.")
    parser.add_argument("--do_test", action='store_true',
                        help="Whether to run eval on the dev set.")    
    parser.add_argument("--evaluate_during_training", action='store_true',
                        help="Run evaluation during training at each logging step.")
    parser.add_argument("--eval_batch_size", default=4, type=int,
                        help="Batch size per GPU/CPU for evaluation.")
    parser.add_argument('--seed', type=int, default=42,
                        help="random seed for initialization")

    

    args = parser.parse_args()

    device = torch.device("cuda")
    args.device = device

    args.output_dir="D:\\adv_ml\\attack-pretrain-models-of-code\GraphCodeBERT\clonedetection\code\saved_models" 
    args.model_type="roberta" 
    args.config_name="microsoft/graphcodebert-base" 
    args.csv_store_path= "./attack_base_result.csv" 
    args.model_name_or_path="microsoft/graphcodebert-base" 
    args.tokenizer_name="microsoft/graphcodebert-base" 
    args.base_model="microsoft/graphcodebert-base" 
    args.train_data_file="../dataset/train_sampled.txt" 
    args.eval_data_file="D:\\adv_ml\\attack-pretrain-models-of-code\GraphCodeBERT\clonedetection\dataset\\test_subs_0_500.txt" 
    args.test_data_file="../dataset/test_sampled.txt" 
    args.code_length = 384 
    args.data_flow_length = 128 
    args.eval_batch_size = 32 
    args.seed = 123456 

    # Set seed
    set_seed(args.seed)

    args.start_epoch = 0
    args.start_step = 0
    checkpoint_last = os.path.join(args.output_dir, 'checkpoint-last')
    if os.path.exists(checkpoint_last) and os.listdir(checkpoint_last):
        args.model_name_or_path = os.path.join(checkpoint_last, 'pytorch_model.bin')
        args.config_name = os.path.join(checkpoint_last, 'config.json')
        idx_file = os.path.join(checkpoint_last, 'idx_file.txt')
        with open(idx_file, encoding='utf-8') as idxf:
            args.start_epoch = int(idxf.readlines()[0].strip()) + 1

        step_file = os.path.join(checkpoint_last, 'step_file.txt')
        if os.path.exists(step_file):
            with open(step_file, encoding='utf-8') as stepf:
                args.start_step = int(stepf.readlines()[0].strip())

        logger.info("reload model from {}, resume from {} epoch".format(checkpoint_last, args.start_epoch))

    config_class, model_class, tokenizer_class = MODEL_CLASSES[args.model_type]
    config = config_class.from_pretrained(args.config_name if args.config_name else args.model_name_or_path,
                                          cache_dir=args.cache_dir if args.cache_dir else None)
    config.num_labels=1
    tokenizer = tokenizer_class.from_pretrained(args.tokenizer_name,
                                                do_lower_case=False,
                                                cache_dir=args.cache_dir if args.cache_dir else None)

    if args.model_name_or_path:
        model = model_class.from_pretrained(args.model_name_or_path,
                                            from_tf=bool('.ckpt' in args.model_name_or_path),
                                            config=config,
                                            cache_dir=args.cache_dir if args.cache_dir else None)    
    else:
        model = model_class(config)

    model=Model(model,config,tokenizer,args)


    checkpoint_prefix = 'checkpoint-best-f1\\model.bin'
    output_dir = os.path.join(args.output_dir, '{}'.format(checkpoint_prefix))  
    model.load_state_dict(torch.load(output_dir), strict=False)
    model.to(args.device)


    ## Load CodeBERT (MLM) model
    codebert_mlm = RobertaForMaskedLM.from_pretrained(args.base_model)
    tokenizer_mlm = RobertaTokenizer.from_pretrained(args.base_model)
    codebert_mlm.to('cuda') 

    ## Load tensor features
    eval_dataset = TextDataset(tokenizer, args, args.eval_data_file)
    ## Load code pairs
    source_codes = get_code_pairs(args.eval_data_file)

    postfix = args.eval_data_file.split('\\')[-1].split('.txt')[0].split("_")
    folder = '\\'.join(args.eval_data_file.split('\\')[:-1]) # 得到文件目录
    subs_path = "D:\\adv_ml\\test_subs_0_500.jsonl"
    substitutes = []
    with open(subs_path) as f:
        for line in f:
            js = json.loads(line.strip())
            substitutes.append(js["substitutes"])
    assert len(source_codes) == len(eval_dataset) == len(substitutes)

    # 现在要尝试计算importance_score了.
    success_attack = 0
    total_cnt = 0


    recoder = Recorder(args.csv_store_path)
    attacker = Attacker(args, model, tokenizer, codebert_mlm, tokenizer_mlm, use_bpe=1, threshold_pred_score=0)
    start_time = time.time()
    query_times = 0
    for index, sample in enumerate(eval_dataset):
        example_start_time = time.time()
        code_pair = source_codes[index]
        substitute = substitutes[index]
        example = sample[0]
        sim_score_dict = sample[1][index]
        code, prog_length, adv_code, true_label, orig_label, temp_label, is_success, variable_names, names_to_importance_score, nb_changed_var, nb_changed_pos, replaced_words = attacker.greedy_attack(example,substitute, code_pair, sim_score_dict)
        attack_type = "Greedy"
        if is_success == -1 and args.use_ga:
            # 如果不成功，则使用gi_attack
            code, prog_length, adv_code, true_label, orig_label, temp_label, is_success, variable_names, names_to_importance_score, nb_changed_var, nb_changed_pos, replaced_words = attacker.ga_attack(example, substitute, code, initial_replace=replaced_words)
            attack_type = "GA"

        example_end_time = (time.time()-example_start_time)/60
        
        print("Example time cost: ", round(example_end_time, 2), "min")
        print("ALL examples time cost: ", round((time.time()-start_time)/60, 2), "min")

        score_info = ''
        if names_to_importance_score is not None:
            for key in names_to_importance_score.keys():
                score_info += key + ':' + str(names_to_importance_score[key]) + ','

        replace_info = ''
        if replaced_words is not None:
            for key in replaced_words.keys():
                replace_info += key + ':' + replaced_words[key] + ','
        print("Query times in this attack: ", model.query - query_times)
        print("All Query times: ", model.query)

        recoder.write(index, code, prog_length, adv_code, true_label, orig_label, temp_label, is_success, variable_names, score_info, nb_changed_var, nb_changed_pos, replace_info, attack_type, model.query - query_times, example_end_time)
        
        query_times = model.query

        if is_success >= -1 :
            # 如果原来正确
            total_cnt += 1
        if is_success == 1:
            success_attack += 1
        
        if total_cnt == 0:
            continue
        print("Success rate: ", 1.0 * success_attack / total_cnt)
        print("Successful items count: ", success_attack)
        print("Total count: ", total_cnt)
        print("Index: ", index)
        print()


if __name__ == '__main__':
    main()