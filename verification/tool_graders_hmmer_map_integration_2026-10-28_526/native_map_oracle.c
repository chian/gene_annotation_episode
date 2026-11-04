/* UNEXECUTED diagnostic recipe, not production execution or a native CLI result.
 * Compile against the retained Infernal 1.1.5 HMMER/Easel tree. The original
 * alimask translation unit supplies options and p7_Alimask_MakeModel2AliMap.
 * This adapter calls native weight/fragment routines; it does not port them.
 */
#define main retained_alimask_cli_main
#include "alimask.c"
#undef main

int main(int argc, char **argv)
{
  ESL_GETOPTS *go = NULL;
  ESL_ALPHABET *abc = NULL;
  ESL_MSAFILE *afp = NULL;
  ESL_MSA *msa = NULL;
  ESL_MSAWEIGHT_CFG *cfg = NULL;
  ESL_MSAWEIGHT_DAT *dat = NULL;
  char *input = NULL, *unused_output = NULL;
  int status, format, do_hand, i, j, length;
  int *map = NULL;

  impl_Init();
  process_commandline(argc, argv, &go, &input, &unused_output);
  if (esl_opt_GetBoolean(go, "--amino")) abc = esl_alphabet_Create(eslAMINO);
  else if (esl_opt_GetBoolean(go, "--dna")) abc = esl_alphabet_Create(eslDNA);
  else if (esl_opt_GetBoolean(go, "--rna")) abc = esl_alphabet_Create(eslRNA);
  else esl_fatal("oracle requires the selected explicit alphabet");
  format = esl_opt_IsOn(go, "--informat") ? esl_msafile_EncodeFormat(esl_opt_GetString(go, "--informat")) : eslMSAFILE_UNKNOWN;
  status = esl_msafile_Open(&abc, input, NULL, format, NULL, &afp);
  if (status != eslOK) esl_msafile_OpenFailure(afp, status);
  status = esl_msafile_Read(afp, &msa);
  if (status != eslOK) esl_msafile_ReadFailure(afp, status);
  cfg = esl_msaweight_cfg_Create();
  dat = esl_msaweight_dat_Create();
  if (cfg == NULL || dat == NULL) esl_fatal("native config allocation failed");
  do_hand = esl_opt_IsOn(go, "--hand");
  cfg->ignore_rf = do_hand ? FALSE : TRUE;
  /* The original CLI never assigns go's --seed to cfg->seed. */
  printf("{\"cli_seed\":%d,\"effective_pb_seed\":%llu,", esl_opt_GetInteger(go, "--seed"), (unsigned long long) cfg->seed);
  status = eslOK;
  if (esl_opt_IsOn(go, "--wnone")) esl_vec_DSet(msa->wgt, msa->nseq, 1.);
  else if (esl_opt_IsOn(go, "--wgiven")) ;
  else if (esl_opt_IsOn(go, "--wpb")) status = esl_msaweight_PB_adv(cfg, msa, dat);
  else if (esl_opt_IsOn(go, "--wgsc")) status = esl_msaweight_GSC(msa);
  else if (esl_opt_IsOn(go, "--wblosum")) status = esl_msaweight_BLOSUM(msa, esl_opt_GetReal(go, "--wid"));
  if (status != eslOK) esl_fatal("native weighting failed with %d", status);
  printf("\"weights\":[");
  for (i = 0; i < msa->nseq; i++) printf("%s%.17g", i ? "," : "", msa->wgt[i]);
  printf("],\"pb\":{\"cons_by_sample\":%d,\"cons_by_all\":%d,\"cons_allcols\":%d,\"rejected_sample\":%d,\"sample_fragment_count\":%d,\"consensus_columns\":[", dat->cons_by_sample, dat->cons_by_all, dat->cons_allcols, dat->rejected_sample, dat->samp_nfrag);
  for (i = 0; i < dat->ncons; i++) printf("%s%d", i ? "," : "", dat->conscols[i]);
  printf("]},");
  if (esl_msa_MarkFragments_old(msa, esl_opt_GetReal(go, "--fragthresh")) != eslOK) esl_fatal("native fragment marking failed");
  printf("\"marked_sequences\":[");
  for (i = 0; i < msa->nseq; i++) {
    printf("%s\"", i ? "," : "");
    for (j = 1; j <= msa->alen; j++) putchar(msa->abc->sym[msa->ax[i][j]]);
    printf("\"");
  }
  map = malloc(sizeof(int) * (msa->alen + 1));
  if (map == NULL) esl_fatal("native map allocation failed");
  length = p7_Alimask_MakeModel2AliMap(msa, do_hand, esl_opt_GetReal(go, "--symfrac"), map);
  printf("],\"map\":[");
  for (i = 0; i < length; i++) printf("%s%d", i ? "," : "", map[i]);
  printf("]}\n");
  free(map);
  esl_msaweight_dat_Destroy(dat);
  esl_msaweight_cfg_Destroy(cfg);
  esl_msa_Destroy(msa);
  esl_msafile_Close(afp);
  esl_alphabet_Destroy(abc);
  esl_getopts_Destroy(go);
  return 0;
}
